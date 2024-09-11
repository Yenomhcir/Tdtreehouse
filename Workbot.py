from telegram import Update, InputFile
from telegram.ext import Updater, CommandHandler, CallbackContext, ConversationHandler, MessageHandler, Filters
from datetime import datetime
import json
import qrcode
import logging
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters
import re

# Configure logging to a file to trace errors
logging.basicConfig(filename='error.log', level=logging.ERROR)

# Conversation states
ASKING_NAME, ASKING_ID, DAY_INVENTORY, NIGHT_INVENTORY = range(4)

# File path to store smokers, Clock in times, inventory and employee data JSON
SMOKERS_FILE = 'smokers.json'
INVENTORY_FILE = 'inventory.json'
EMPLOYEES_FILE = 'employees.json'
CLOCK_TIMES_FILE = 'clock_times.json'
TRANSACTION_FILE = "transactions.json"

# Global variables to store smoker and inventory data
smokers = {}
day_inventory = {}
night_inventory = {}
inventory = {}


# Dictionary to store employee names and their roles
employees = {}

def parse_date(date_str):
    print(f"Parsing date: {date_str}")  # Debugging statement
    try:
        # Expect the date format to be 'YYYY-MM-DD HH:MM:SS'
        parsed_date = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        print(f"Successfully parsed date: {parsed_date}")  # Debugging statement
        return parsed_date
    except ValueError:
        print("Failed to parse date.")  # Debugging statement
        return None  # Return None if the date is in an invalid format



# Function to load clock in/out data from JSON
def load_clock_times():
    global clock_in_times, worked_times
    try:
        with open(CLOCK_TIMES_FILE, 'r') as f:
            data = json.load(f)
            clock_in_times = data.get("clock_times", {})
            worked_times = data.get("worked_times", {})
    except FileNotFoundError:
        clock_in_times = {}
        worked_times = {}

# Function to save clock in/out data to JSON
def save_clock_times():
    with open(CLOCK_TIMES_FILE, 'w') as f:
        json.dump({
            "clock_times": clock_times,
            "worked_times": worked_times
        }, f, indent=4)

# Function to load smokers from JSON
def load_smokers():
    global smokers
    try:
        with open(SMOKERS_FILE, 'r') as f:
            smokers = json.load(f)
    except FileNotFoundError:
        smokers = {}

# Function to save smokers to JSON
def save_smokers():
    with open(SMOKERS_FILE, 'w') as f:
        json.dump(smokers, f, indent=4)


def load_inventory():
    global day_inventory, night_inventory, inventory
    try:
        with open(INVENTORY_FILE, 'r', encoding='utf-8') as f:  # Use 'utf-8' encoding
            data = json.load(f)
            day_inventory = data.get("day_inventory", {})
            night_inventory = data.get("night_inventory", {})
            inventory = data.get("inventory", inventory)  # Load inventory if it exists in the JSON

            # Add debugging print statements
            print("Day Inventory Loaded: ", day_inventory)  # Print day inventory
            print("Night Inventory Loaded: ", night_inventory)  # Print night inventory
            print("Main Inventory Loaded: ", inventory)  # Print the main inventory (regular and exotic flowers)
    except FileNotFoundError:
        print("Inventory file not found.")  # Notify that the file doesn't exist yet
        pass  # File does not exist yet
    except Exception as e:
        print(f"Error loading inventory: {str(e)}")  # Catch any other potential errors



def edit_clockin(update: Update, context: CallbackContext) -> None:
    print(f"Raw context.args: {context.args}")  # Log raw arguments

    # Ensure we have the correct number of arguments (FirstName, LastName, Date, Time)
    if len(context.args) < 5:
        update.message.reply_text(
            "📋 Usage: /edit_clockin FirstName LastName YYYY-MM-DD HH:MM:SS\n\nExample: /edit_clockin John Doe 2024-09-09 09:00:00")
        print(f"Received fewer than 5 arguments. Raw context.args: {context.args}")  # Log issue
        return

    # Extract the employee's name (first and last name)
    first_name = context.args[0]
    last_name = context.args[1]
    employee_name = f"{first_name} {last_name}"

    # Extract the date and time from the provided arguments
    date_part = context.args[2]
    time_part = context.args[3]

    # Ensure time includes seconds, if not provided
    if len(context.args) == 5:
        seconds_part = context.args[4]
        time_part = f"{time_part}:{seconds_part}"

    # Combine date and time into one string
    date_time_str = f"{date_part} {time_part}"

    print(f"Entering the /edit_clockin command...")
    print(f"Employee Name: {employee_name}")
    print(f"New Clock-in Time (string): {date_time_str}")

    # Check if the employee exists
    if employee_name not in employees:
        update.message.reply_text(f"❌ **{employee_name}** is not an employee. Please add them first.")
        return

    # Parse the provided datetime
    try:
        print(f"Parsing date: {date_time_str}")
        new_clockin_time = datetime.strptime(date_time_str, '%Y-%m-%d %H:%M:%S')
        print(f"Date parsed successfully: {new_clockin_time}")
    except ValueError:
        print(f"Failed to parse date.")
        update.message.reply_text("❌ Invalid date format. Please use 'YYYY-MM-DD HH:MM:SS'.")
        return

    # Update the clock-in time
    clock_in_times[employee_name] = new_clockin_time.strftime('%Y-%m-%d %H:%M:%S')
    print(f"Clock-in time updated for {employee_name}: {clock_in_times[employee_name]}")

    update.message.reply_text(
        f"✅ **{employee_name}'s** clock-in time has been updated to {new_clockin_time.strftime('%Y-%m-%d %H:%M:%S')}.")


def clock_in(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        update.message.reply_text("Please use the format /Clock_in FirstName LastName")
        return

    employee_name = " ".join(context.args)

    if employee_name not in employees:
        update.message.reply_text(f"{employee_name} is not an employee. Please add them first.")
        return

    current_time = datetime.now()
    clock_in_times[employee_name] = current_time.strftime('%Y-%m-%d %H:%M:%S')  # Save time as string

    # Save the clock-in time to the storage (e.g., JSON, DB, etc.)
    # save_data()

    message = f"{employee_name} has clocked in at {current_time.strftime('%Y-%m-%d %H:%M:%S')}."
    update.message.reply_text(message)


# Function to clock out an employee
def clock_out(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        update.message.reply_text("Please use the format /clock_out FirstName LastName")
        return

    employee_name = " ".join(context.args)

    if employee_name not in employees:
        update.message.reply_text(f"{employee_name} is not an employee. Please add them first.")
        return

    if employee_name not in clock_in_times:
        update.message.reply_text(f"{employee_name} has not clocked in.")
        return

    current_time = datetime.now()
    start_time = datetime.strptime(clock_in_times.pop(employee_name), '%Y-%m-%d %H:%M:%S')
    time_worked = current_time - start_time

    if employee_name in worked_times:
        worked_times[employee_name] += time_worked
    else:
        worked_times[employee_name] = time_worked

    # Save clock-out data to JSON
    save_clock_times()

    message = f"{employee_name} has clocked out at {current_time.strftime('%Y-%m-%d %H:%M:%S')}.\n"
    message += f"Time worked: {str(time_worked).split('.')[0]} hours."
    update.message.reply_text(message)

# Function to add a smoker
def add_smoker(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        update.message.reply_text("📋 Usage: /add_smoker FirstName LastName 4-digit-ID\n\nExample: /add_smoker John Doe 1111")
        return

    first_name, last_name, smoker_id = context.args
    full_name = f"{first_name} {last_name}"

    if len(smoker_id) != 4 or not smoker_id.isdigit():
        update.message.reply_text("Please provide a valid 4-digit ID.")
        return
    if smoker_id in smokers:
        update.message.reply_text("This ID is already in use.")
        return

    smokers[smoker_id] = {"name": full_name, "points": 0}
    save_smokers()  # Save smokers to JSON

    update.message.reply_text(f"✅ **{full_name}** has been added as a smoker with ID {smoker_id}.")

# Function to remove a smoker
def remove_smoker(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        update.message.reply_text("📋 Usage: /remove_smoker [ID or Name]\n\nExample: /remove_smoker 1111 or /remove_smoker John Doe")
        return

    identifier = " ".join(context.args).strip()  # Join the arguments in case it's a full name
    to_remove = None

    # Check if the identifier is a 4-digit ID
    if identifier.isdigit() and len(identifier) == 4:
        if identifier in smokers:
            to_remove = identifier
    else:
        # If it's not an ID, treat it as a name and search by full name
        for smoker_id, details in smokers.items():
            if details['name'].lower() == identifier.lower():
                to_remove = smoker_id
                break

    if to_remove:
        del smokers[to_remove]  # Remove the smoker by their ID
        save_smokers()  # Save smokers to JSON after removal
        update.message.reply_text(f"✅ Smoker {identifier} has been removed.")
    else:
        update.message.reply_text(f"❌ Smoker {identifier} not found.")



# Function to remove a regular flower
def remove_flower(update: Update, context: CallbackContext) -> None:
    print("Received /remove_flower command")  # Debugging statement

    if len(context.args) < 1:
        update.message.reply_text("📋 Usage: /remove_flower FlowerName\n\nExample: /remove_flower Wedding Cake 🎂")
        print("Error: No flower name provided")  # Debugging statement
        return

    flower_name_input = " ".join(context.args).strip()

    print(f"Flower name to remove: {flower_name_input}")  # Debugging statement

    # Check if the flower exists in the regular category
    found_flower = None
    for flower_name in inventory["flower"]["regular"].keys():
        if flower_name == flower_name_input:
            found_flower = flower_name
            break

    if found_flower:
        # Remove the regular flower
        del inventory["flower"]["regular"][found_flower]

        # Save the updated inventory to the file
        save_inventory()

        print(f"Removed flower '{found_flower}' from the menu")  # Debugging statement
        update.message.reply_text(f"✅ Removed flower '{found_flower}' from the menu.")
    else:
        update.message.reply_text(f"❌ Flower '{flower_name_input}' not found in the regular flower menu.")
        print(f"Error: Flower '{flower_name_input}' not found")  # Debugging statement



def view_smokers(update: Update, context: CallbackContext) -> None:
    print("Received /view_smokers command.")  # Trace start of the function

    # Print the entire smokers dictionary to diagnose its structure
    print(f"Smokers data: {smokers}")

    # Check if smokers list is empty
    if not smokers:
        print("No smokers found.")  # Trace when no smokers are present
        update.message.reply_text("🚬 No smokers have been added yet.")
        return

    message = "🚬 **Smokers**:\n\n"

    # Iterate over the smokers
    for user_id, details in smokers.items():
        print(f"Processing smoker ID: {user_id}, Details: {details}")  # Print each smoker's details

        # Check the structure of each entry and log if 'name' or 'points' is missing
        if 'name' not in details:
            print(f"Missing 'name' key for smoker ID: {user_id}")  # Diagnose missing 'name' key
            logging.error(f"Missing 'name' key for smoker ID: {user_id}, Details: {details}")
            name = "Unknown"
        else:
            name = details['name']

        points = details.get('points', 0)  # Safely retrieve 'points', defaulting to 0 if missing

        print(f"Smoker {user_id} - Name: {name}, Points: {points}")  # Log smoker details
        message += f"ID: {user_id} | Name: {name} | Points: {points} points\n"

    print(f"Final message to send: {message}")  # Trace the final message that will be sent
    update.message.reply_text(message, parse_mode='Markdown')


def day_inventory_start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Starting morning inventory. Please enter the amounts for each product.")
    context.user_data["inventory_stage"] = "day"
    context.user_data["inventory_list"] = list(inventory["flower"]["regular"].keys()) + list(inventory["flower"]["Exotic"].keys())
    context.user_data["day_inventory"] = {}  # Save day inventory input here
    ask_next_product(update, context)
    return DAY_INVENTORY


def night_inventory_start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Starting night inventory. Please enter the amounts for each product.")
    context.user_data["inventory_stage"] = "night"
    context.user_data["inventory_list"] = list(inventory["flower"]["regular"].keys()) + list(inventory["flower"]["Exotic"].keys())
    context.user_data["night_inventory"] = {}  # Save night inventory input here
    ask_next_product(update, context)
    return NIGHT_INVENTORY


# Function to view current inventory
def view_inventory(update: Update, context: CallbackContext) -> None:
    message = "🌿 **Current Inventory Levels**:\n\n"

    # Regular Flower Section
    message += "🌱 **Regular Flower**:\n"
    for product, sizes in inventory["flower"]["regular"].items():
        stock = sizes.get("Stock", 0)
        message += f" - {product}: {stock} grams left\n"

    # Exotic Flower Section
    message += "\n🌸 **Exotic Flower**:\n"
    for product, sizes in inventory["flower"]["Exotic"].items():
        stock = sizes.get("Stock", 0)
        message += f" - {product}: {stock} grams left\n"

    update.message.reply_text(message, parse_mode='Markdown')

# Helper function to ask for the next product during inventory
def ask_next_product(update: Update, context: CallbackContext) -> int:
    current_product = context.user_data.get("current_product_index", 0)
    product_list = context.user_data.get("inventory_list")

    if current_product < len(product_list):
        product_name = product_list[current_product]
        context.user_data["current_product_name"] = product_name
        update.message.reply_text(f"Enter amount for {product_name}:")
        context.user_data["current_product_index"] = current_product + 1

        # Ensure correct state return based on inventory stage
        return DAY_INVENTORY if context.user_data["inventory_stage"] == "day" else NIGHT_INVENTORY
    else:
        return complete_inventory(update, context)

# Function to complete the inventory process
def complete_inventory(update: Update, context: CallbackContext) -> int:
    inventory_stage = context.user_data.get("inventory_stage")
    if inventory_stage == "day":
        update.message.reply_text("Morning inventory completed.")
    else:
        update.message.reply_text("Night inventory completed.")

    save_inventory()  # Save the inventory to JSON after completion
    return ConversationHandler.END

# Function to cancel the inventory process
def cancel_inventory(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Inventory process has been canceled.")
    return ConversationHandler.END
def process_inventory_input(update: Update, context: CallbackContext) -> int:
    product = context.user_data.get("current_product_name")
    print(f"Received input for: {product}")  # Debugging statement

    try:
        amount = int(update.message.text)
        print(f"Amount entered: {amount}")  # Debugging statement
    except ValueError:
        update.message.reply_text("Please enter a valid number.")
        # Ensure the correct inventory stage is returned
        return DAY_INVENTORY if context.user_data.get("inventory_stage") == "day" else NIGHT_INVENTORY

    # Update the inventory based on the stage (morning or night)
    if context.user_data.get("inventory_stage") == "day":
        context.user_data["day_inventory"][product] = amount
        print(f"Day inventory updated for {product}: {amount}")  # Debugging statement
    else:
        context.user_data["night_inventory"][product] = amount
        print(f"Night inventory updated for {product}: {amount}")  # Debugging statement

    # Update the main inventory
    for product_type in ["regular", "Exotic"]:
        if product in inventory["flower"][product_type]:
            inventory["flower"][product_type][product]["Stock"] = amount
            print(f"Main inventory updated for {product} in {product_type}: {amount}")  # Debugging statement

    save_inventory()  # Save inventory to JSON after each update

    # Proceed to the next product
    return ask_next_product(update, context)


def save_inventory():
    global day_inventory, night_inventory, inventory
    with open(INVENTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            "day_inventory": day_inventory,
            "night_inventory": night_inventory,
            "inventory": inventory
        }, f, ensure_ascii=False, indent=4)
    print("Inventory saved to JSON")  # Debugging statement


inventory_handler = ConversationHandler(
    entry_points=[
        CommandHandler('day_inventory', day_inventory_start),
        CommandHandler('night_inventory', night_inventory_start)
    ],
    states={
        DAY_INVENTORY: [MessageHandler(Filters.text & ~Filters.command, process_inventory_input)],
        NIGHT_INVENTORY: [MessageHandler(Filters.text & ~Filters.command, process_inventory_input)]
    },
    fallbacks=[CommandHandler('cancel_inventory', cancel_inventory)]
)



def complete_inventory(update: Update, context: CallbackContext) -> int:
    inventory_stage = context.user_data.get("inventory_stage")

    if inventory_stage == "day":
        update.message.reply_text("Morning inventory completed.")
    elif inventory_stage == "night":
        update.message.reply_text("Night inventory completed.")

    save_inventory()  # Save the inventory to JSON after completion
    return ConversationHandler.END

# Placeholder function to calculate sold amount based on recorded sales
def calculate_sold_amount(product):
    # This would be based on the actual sales made during the day
    # For now, returning a dummy number for illustration purposes
    return 5  # Example value


def process_refund(update: Update, context: CallbackContext):
    try:
        args = context.args
        flower_name = args[0]
        quantity = float(args[1])
        price = float(args[2])

        # Determine if the product is "regular" or "exotic"
        flower_type = ""
        if flower_name in inventory["flower"]["regular"]:
            flower_type = "regular"
        elif flower_name in inventory["flower"]["Exotic"]:
            flower_type = "Exotic"
        else:
            update.message.reply_text(f"❌ Product '{flower_name}' not found in inventory.")
            return

        # Process the refund and remove points from smokers
        result = refund_product(flower_name, quantity, price, flower_type, update)
        update.message.reply_text(result)

    except (IndexError, ValueError) as e:
        update.message.reply_text("Please provide valid input. Example: /refund Sherbacio 3.5 20")
    save_inventory()
    save_smokers()



def update_stock(flower_name, quantity, flower_type):
    load_inventory()  # Load inventory

    if flower_type == "regular":
        if flower_name in inventory["flower"]["regular"]:
            inventory["flower"]["regular"][flower_name]["Stock"] -= quantity
    elif flower_type == "Exotic":
        if flower_name in inventory["flower"]["Exotic"]:
            inventory["flower"]["Exotic"][flower_name]["Stock"] -= quantity

def sell_product(update: Update, context: CallbackContext):
    try:
        # Extract smoker name or ID, flower name, quantity, and price
        command_args = context.args
        if len(command_args) < 4:
            update.message.reply_text(
                "Please provide smoker name/ID, flower name, quantity, and price. Example: /sell 1024 Sherbacio 🍧 3.5 25")
            return

        smoker_input = command_args[0].strip()  # Can be either name or ID
        flower_name_input = " ".join(command_args[1:-2]).strip()  # Flower name
        quantity_str = command_args[-2].strip()  # Quantity as a string
        price_str = command_args[-1].strip()  # Price as a string

        try:
            quantity = float(quantity_str)  # Convert to float to handle decimal quantities
            price = float(price_str)
        except ValueError:
            update.message.reply_text("Please provide valid numeric values for quantity and price.")
            return

        load_inventory()  # Load the inventory

        # Clean the flower name input and inventory names for comparison
        flower_name_input_cleaned = clean_name(flower_name_input)

        smoker_name = smoker_input
        smoker_id = None
        member_found = False  # Initialize as False

        # Check if the smoker_input is a 4-digit ID or a name
        if smoker_input.isdigit() and len(smoker_input) == 4:  # It's an ID
            smoker_id = smoker_input
            if smoker_id in smokers:
                smoker_name = smokers[smoker_id]["name"]
                member_found = True  # Set to True if smoker found
            else:
                update.message.reply_text(
                    f"⚠️ Smoker with ID {smoker_id} not found. Proceeding without membership points.")
        else:  # It's a name
            for id, details in smokers.items():
                if details["name"].lower() == smoker_name.lower():
                    smoker_name = details["name"]  # Match the exact name
                    smoker_id = id
                    member_found = True  # Set to True if smoker found
                    break

            if not member_found:
                update.message.reply_text(f"⚠️ Smoker '{smoker_name}' not found. Proceeding without membership points.")

        # If the smoker is a member, add points to their account
        if member_found:
            points_earned = int(price)  # Assuming 1 point per $1 spent
            modify_points(smoker_id, "add", points_earned)
            update.message.reply_text(f"🏆 {points_earned} points have been added to {smoker_name}'s account!")
        else:
            update.message.reply_text(f"✅ Sale completed without points for {smoker_name}.")
    except Exception as e:
        update.message.reply_text(f"An error occurred: {str(e)}")

    def refund_product(update: Update, context: CallbackContext):
        try:
            # Extract the smoker name/ID, flower name, quantity, and price
            command_args = context.args
            if len(command_args) < 4:
                update.message.reply_text(
                    "Please provide smoker name/ID, flower name, quantity, and price. Example: /refund 1024 Sherbacio 🍧 3.5 25")
                return

            smoker_input = command_args[0].strip()  # Can be either name or ID
            flower_name_input = " ".join(command_args[1:-2]).strip()  # Flower name
            quantity_str = command_args[-2].strip()  # Quantity as a string
            price_str = command_args[-1].strip()  # Price as a string

            try:
                quantity = float(quantity_str)  # Convert to float to handle decimal quantities
                price = float(price_str)
            except ValueError:
                update.message.reply_text("Please provide valid numeric values for quantity and price.")
                return

            load_inventory()  # Load the inventory

            # Clean the flower name input and inventory names for comparison
            flower_name_input_cleaned = clean_name(flower_name_input)

            smoker_name = smoker_input
            smoker_id = None
            member_found = False  # Initialize as False

            # Check if the smoker_input is a 4-digit ID or a name
            if smoker_input.isdigit() and len(smoker_input) == 4:  # It's an ID
                smoker_id = smoker_input
                if smoker_id in smokers:
                    smoker_name = smokers[smoker_id]["name"]
                    member_found = True
                else:
                    update.message.reply_text(
                        f"⚠️ Smoker with ID {smoker_id} not found. Proceeding without membership points deduction.")
            else:  # It's a name
                for id, details in smokers.items():
                    if details["name"].lower() == smoker_name.lower():
                        smoker_name = details["name"]  # Match the exact name
                        smoker_id = id
                        member_found = True
                        break

                if not member_found:
                    update.message.reply_text(
                        f"⚠️ Smoker '{smoker_name}' not found. Proceeding without membership points deduction.")

            # Check if the flower is in inventory by comparing cleaned names
            found_flower = None
            for product_type in ["regular", "Exotic"]:
                for flower_name, flower_data in inventory["flower"][product_type].items():
                    flower_name_cleaned = clean_name(flower_name)

                    if flower_name_cleaned == flower_name_input_cleaned:
                        found_flower = flower_data
                        flower_name = flower_name  # Retain the original name with emoji for the response
                        break

            if found_flower:
                # Check if the specific weight is available (convert weights to floats)
                available_weights = [float(weight) for weight in found_flower.keys() if weight != "Stock"]

                if quantity in available_weights:
                    update.message.reply_text(f"✅ Refunded {quantity}g of {flower_name} for ${price} to {smoker_name}.")

                    # Increase the stock by the refunded quantity
                    found_flower["Stock"] += quantity

                    # Save the updated inventory
                    save_inventory()

                    # Log the refund in the transactions.json
                    log_transaction("Refund", flower_name, quantity, price, smoker_name)

                    # If the smoker is a member, deduct points from their account (1 point per $1 refunded)
                    if member_found:
                        points_deducted = int(price)  # Assuming 1 point per $1 refunded
                        modify_points(smoker_id, "deduct", points_deducted)
                        update.message.reply_text(
                            f"⚠️ {points_deducted} points have been deducted from {smoker_name}'s account.")
                else:
                    update.message.reply_text(
                        f"❌ Product '{flower_name}' with weight {quantity}g not found in inventory.")
            else:
                update.message.reply_text(f"❌ Product '{flower_name_input}' not found in inventory.")
        except Exception as e:
            update.message.reply_text(f"An error occurred: {str(e)}")

    save_inventory()  # Save updated inventory
def log_transaction(transaction_type, product, quantity, price, smoker_name=None):
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    try:
        with open(TRANSACTION_FILE, 'r') as file:
            transactions = json.load(file)
    except FileNotFoundError:
        transactions = []

    # Create a new transaction entry
    transaction = {
        "date": date,
        "type": transaction_type,  # Sale or Refund
        "product": product,
        "quantity": quantity,
        "price": price,
        "smoker_name": smoker_name
    }

    transactions.append(transaction)

    # Save the updated transactions list
    with open(TRANSACTION_FILE, 'w') as file:
        json.dump(transactions, file, indent=4)

def clear_transactions(update: Update, context: CallbackContext) -> None:
    # Check if the user is an admin
    user_id = update.message.from_user.id
    admin_ids = [908551450, 5120023328]  # Replace with your actual admin IDs

    if user_id not in admin_ids:
        update.message.reply_text("❌ You are not authorized to clear transactions.")
        return

    # Clear the transactions file
    try:
        with open(TRANSACTION_FILE, 'w') as file:
            json.dump([], file, indent=4)  # Write an empty list to clear the transactions
        update.message.reply_text("✅ All transactions have been cleared.")
    except Exception as e:
        update.message.reply_text(f"❌ Failed to clear transactions: {str(e)}")

def edit_clockin(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        update.message.reply_text(
            "📋 Usage: /edit_clockin FirstName LastName 'YYYY-MM-DD HH:MM:SS'\n\nExample: /edit_clockin John Doe '2024-09-07 09:00:00'")
        return

    # Capture and print the user input
    employee_name = " ".join(context.args[0:2])
    new_clockin_time_str = context.args[2]

    print(f"Employee Name: {employee_name}")
    print(f"New Clock-in Time (string): {new_clockin_time_str}")

    # Check if employee exists
    if employee_name not in employees:
        update.message.reply_text(f"❌ **{employee_name}** is not an employee. Please add them first.")
        return

    try:
        # Parse the provided datetime and print the parsed date for debugging
        print(f"Parsing date: {new_clockin_time_str}")
        new_clockin_time = datetime.strptime(new_clockin_time_str, '%Y-%m-%d %H:%M:%S')
        print(f"Successfully parsed date: {new_clockin_time}")
    except ValueError as e:
        print(f"Failed to parse date. Error: {str(e)}")
        update.message.reply_text("❌ Invalid date format. Please use 'YYYY-MM-DD HH:MM:SS'.")
        return

    # Update the clock-in time
    clock_in_times[employee_name] = new_clockin_time
    update.message.reply_text(f"✅ **{employee_name}'s** clock-in time has been updated to {new_clockin_time_str}.")

# Load clock-in and worked times at startup
load_clock_times()

# Function to save employees to JSON
def save_employees():
    with open(EMPLOYEES_FILE, 'w') as f:
        json.dump(employees, f, indent=4)

# Function to load employees from JSON
def load_employees():
    global employees
    try:
        with open(EMPLOYEES_FILE, 'r') as f:
            employees = json.load(f)
    except FileNotFoundError:
        employees = {}

# Function to add an employee with a role
def add_employee(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        update.message.reply_text(
            "📋 Usage: /add_employee FirstName LastName Role\n\nExample: /add_employee John Doe CEO")
        return

    first_name, last_name, role = context.args[0], context.args[1], context.args[2].capitalize()
    employee_name = f"{first_name} {last_name}"

    # Add employee to the employees dictionary with their role
    employees[employee_name] = role

    # Save employee data to JSON
    save_employees()

    update.message.reply_text(f"✅ **{employee_name}** has been added as {role}.", parse_mode='Markdown')


# Function to remove an employee
def remove_employee(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 2:
        update.message.reply_text("📋 Usage: /remove_employee FirstName LastName\n\nExample: /remove_employee John Doe")
        return

    employee_name = " ".join(context.args)

    if employee_name in employees:
        del employees[employee_name]
        save_employees()
        update.message.reply_text(f"✅ {employee_name} has been removed from the employee list.")
    else:
        update.message.reply_text(f"❌ {employee_name} is not in the employee list.")


# Function to view all employees and their roles
def view_staff(update: Update, context: CallbackContext) -> None:
    if not employees:
        update.message.reply_text("No employees have been added yet.")
        return

    message = "T&D Treehouse Staff 🌲\n\n"
    for employee, role in employees.items():
        message += f" - {employee}: {role}\n"

    update.message.reply_text(message, parse_mode='Markdown')


# Function to handle the /menu command
def menu(update: Update, context: CallbackContext) -> None:
    # Load the inventory before displaying the menu
    load_inventory()

    # Debugging: Print the inventory contents
    print("Inventory contents in /menu:", inventory)  # Debugging

    if "flower" not in inventory or not inventory["flower"]["regular"]:
        update.message.reply_text("🌿 No flower products available at the moment.")
        return

    message = "🌲 **T&D Treehouse Menu**:\n\n"

    # Regular Flower Section
    message += "🌱 **Regular Flower**:\n"
    for product, sizes in inventory["flower"]["regular"].items():
        message += f"**{product}**:\n"
        for size, price in sizes.items():
            if size != "Stock":  # Skip the stock information
                message += f" - {size} grams: **${price}**\n"
        message += "\n"

    # Exotic Flower Section
    if "Exotic" in inventory["flower"] and inventory["flower"]["Exotic"]:
        message += "🌸 **Exotic**:\n"
        for product, sizes in inventory["flower"]["Exotic"].items():
            message += f"**{product}**:\n"
            for size, price in sizes.items():
                if size != "Stock":  # Skip the stock information
                    message += f" - {size} grams: **${price}**\n"
            message += "\n"

    update.message.reply_text(message, parse_mode='Markdown')


def view_smokers(update: Update, context: CallbackContext) -> None:
    if not smokers:
        update.message.reply_text("🚬 No smokers have been added yet.")
        return

    message = "🚬 **Smokers**:\n\n"
    for user_id, details in smokers.items():
        message += f"ID: {user_id} | Name: {details['name']} | Points: {details['points']} points\n"

    update.message.reply_text(message, parse_mode='Markdown')


# Add Inventory
def add_inventory(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 2:
        update.message.reply_text("📋 Usage: /add_inventory ProductName Quantity\n\nExample: /add_inventory Wedding Cake 50")
        return

    product_name, quantity = context.args[0], int(context.args[1])

    # Check if product exists in regular or exotic inventory
    found_product = None
    for product_type in ["regular", "Exotic"]:
        if product_name in inventory["flower"][product_type]:
            found_product = inventory["flower"][product_type][product_name]
            break

    if found_product:
        found_product["Stock"] += quantity
        save_inventory()  # Save inventory after adding stock
        update.message.reply_text(f"✅ Added {quantity} grams to {product_name}. New Stock: {found_product['Stock']} grams.")
    else:
        update.message.reply_text(f"❌ Product {product_name} not found in inventory.")


# Function to check inventory levels (called by the job queue, passing only context)
def job_check_inventory_levels(context: CallbackContext):
    message = "⚠️ **Low Stock Alert**:\n\n"
    low_stock = False

    # Check stock for regular flowers (notify if stock < 28 grams)
    for product, details in inventory["flower"]["regular"].items():
        if details["Stock"] < 28:
            message += f" - {product}: {details['Stock']} grams left (Regular)\n"
            low_stock = True

    # Check stock for exotic flowers (notify if stock < 7 grams)
    for product, details in inventory["flower"]["Exotic"].items():
        if details["Stock"] < 7:
            message += f" - {product}: {details['Stock']} grams left (Exotic)\n"
            low_stock = True

    # Send alert if any product is low in stock
    if low_stock:
        chat_id = context.job.context['chat_id']
        context.bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')

def check_inventory(update: Update, context: CallbackContext) -> None:
    # Ensure the user provides a category to check
    if len(context.args) < 1:
        update.message.reply_text("Usage: /check_inventory [category]\nExample: /check_inventory Flower")
        return

    category = context.args[0].lower()  # Get the category and convert it to lowercase
    load_inventory()  # Load the latest inventory

    # Initialize message and flag for if stock is found
    message = f"📦 **Inventory for {category.capitalize()}**:\n\n"
    found_stock = False

    # Check the category and display relevant stock
    if category == "flower":
        # Regular Flowers
        message += "🌱 **Regular Flower**:\n"
        for product, details in inventory["flower"]["regular"].items():
            stock = details.get("Stock", 0)
            message += f" - {product}: {stock} grams left\n"
            found_stock = True

        # Exotic Flowers
        message += "\n🌸 **Exotic Flower**:\n"
        for product, details in inventory["flower"]["Exotic"].items():
            stock = details.get("Stock", 0)
            message += f" - {product}: {stock} grams left\n"
            found_stock = True

    elif category == "edibles":
        # Check if the edibles category exists
        if "edibles" in inventory:
            message += "🍬 **Edibles**:\n"
            for product, details in inventory["edibles"].items():
                stock = details.get("Stock", 0)
                message += f" - {product}: {stock} units left\n"
                found_stock = True
        else:
            message += "No edibles inventory found.\n"

    elif category == "carts":
        # Check if the carts category exists
        if "carts" in inventory:
            message += "🛒 **Carts**:\n"
            for product, details in inventory["carts"].items():
                stock = details.get("Stock", 0)
                message += f" - {product}: {stock} units left\n"
                found_stock = True
        else:
            message += "No carts inventory found.\n"

    else:
        # If the category isn't recognized
        update.message.reply_text(f"Unknown category '{category}'. Please use one of the following: Flower, Edibles, Carts.")
        return

    # If stock is found, display it, otherwise notify that the category is empty
    if found_stock:
        update.message.reply_text(message, parse_mode='Markdown')
    else:
        update.message.reply_text(f"❌ No items found in {category.capitalize()} inventory.", parse_mode='Markdown')


# Schedule the inventory check with the job queue
def start_inventory_check(updater, chat_id, interval=3600):
    job_queue = updater.job_queue
    job_queue.run_repeating(job_check_inventory_levels, interval=interval, first=0, context={'chat_id': chat_id})


# Reset inventory function
def reset_inventory(update: Update, context: CallbackContext):
    # Reset regular and exotic flower stock to 0
    for product_type in ["regular", "Exotic"]:
        for product in inventory["flower"][product_type].keys():
            inventory["flower"][product_type][product]["Stock"] = 0

    save_inventory()  # Save the updated inventory to JSON after resetting
    update.message.reply_text("✅ All inventory has been reset to 0 and saved.")


# Function to reset stock counts for regular and exotic flowers
def reset_flower(update: Update, context: CallbackContext) -> None:
    for product in inventory["flower"]["regular"].keys():
        inventory["flower"]["regular"][product]["Stock"] = 0  # Reset stock to zero

    save_inventory()  # Save the changes
    update.message.reply_text("✅ All regular flower stock counts have been reset to zero.")


def reset_exotic(update: Update, context: CallbackContext) -> None:
    for product in inventory["flower"]["Exotic"].keys():
        inventory["flower"]["Exotic"][product]["Stock"] = 0  # Reset stock to zero

    save_inventory()  # Save the changes
    update.message.reply_text("✅ All exotic flower stock counts have been reset to zero.")


# Function to check for rewards based on smoker points
def check_for_rewards(smoker_name):
    points = smokers[smoker_name]

    if points >= 200:
        message = f"🎉 **{smoker_name}** has earned 200 points! You qualify for $20 off your next purchase."
    elif points >= 150:
        message = f"🎉 **{smoker_name}** has earned 150 points! You qualify for $15 off your next purchase."
    elif points >= 100:
        message = f"🎉 **{smoker_name}** has earned 100 points! You qualify for $10 off your next purchase."
    else:
        return

    # Send the reward notification
    update.message.reply_text(message)


# View smoker points by ID
def view_points(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 1:
        update.message.reply_text("Usage: /view_points [4-digit ID]")
        return

    customer_id = context.args[0]
    if customer_id in smokers:
        points = smokers[customer_id]["points"]
        full_name = smokers[customer_id]["name"]
        update.message.reply_text(f"{full_name} has {points} points.")
    else:
        update.message.reply_text("Invalid ID. Please try again.")


# Admin function to redeem smoker points
def redeem_points(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    admin_ids = [908551450, 5120023328]  # Example admin IDs

    if user_id not in admin_ids:
        update.message.reply_text("You are not authorized to redeem points.")
        return

    if len(context.args) != 2:
        update.message.reply_text("Usage: /redeem_points [4-digit ID] [Points to Redeem]")
        return

    customer_id, points_to_redeem = context.args[0], int(context.args[1])

    if customer_id in smokers:
        if smokers[customer_id]["points"] >= points_to_redeem:
            smokers[customer_id]["points"] -= points_to_redeem
            save_smokers()  # Save updated points to JSON
            update.message.reply_text(f"{points_to_redeem} points redeemed for ID: {customer_id}. Remaining points: {smokers[customer_id]['points']}")
        else:
            update.message.reply_text(f"Not enough points. Current balance: {smokers[customer_id]['points']}")
    else:
        update.message.reply_text("Invalid ID.")

# Assuming 1 point per $1 spent
if member_found:
    points_earned = int(price)
    response = modify_points(smoker_id, "add", points_earned)
    update.message.reply_text(f"🏆 {points_earned} points have been added to {smoker_name}'s account!\n{response}")

def modify_points(smoker_id, action, points):
    """
    Modifies the points of a smoker.
    - smoker_id: The ID of the smoker (4-digit).
    - action: 'add' or 'deduct' to increase or decrease points.
    - points: The number of points to add or deduct.
    """
    if smoker_id not in smokers:
        return f"Smoker with ID {smoker_id} not found."

    if action == "add":
        smokers[smoker_id]["points"] += points
    elif action == "deduct":
        smokers[smoker_id]["points"] -= points
    else:
        return "Invalid action. Use 'add' or 'deduct'."

    save_smokers()  # Save updated smokers data to file

    return f"Successfully {action}ed {points} points to smoker with ID {smoker_id}. Total points: {smokers[smoker_id]['points']}"


# Function to add a regular flower to the inventory
def add_flower(update: Update, context: CallbackContext) -> None:
    print("Received /add_flower command")  # Debugging statement

    if len(context.args) < 2:
        update.message.reply_text("📋 Usage: /add_flower FlowerName StockAmount\n\nExample: /add_flower Wedding Cake 50")
        print("Error: Incorrect number of arguments")  # Debugging statement
        return

    # Join all parts of the flower name before the last argument (which is the stock amount)
    flower_name = " ".join(context.args[:-1])  # Join all args except the last one
    try:
        stock_amount = int(context.args[-1])  # The last argument should be the stock amount
    except ValueError:
        update.message.reply_text("❌ Invalid stock amount. Please provide a number.")
        print("Error: Invalid stock amount")  # Debugging statement
        return

    print(f"Flower name received: {flower_name}")  # Debugging statement
    print(f"Stock amount received: {stock_amount}")  # Debugging statement

    # Check if the flower already exists in the regular category
    if flower_name in inventory["flower"]["regular"]:
        update.message.reply_text(f"❌ Flower '{flower_name}' already exists in the regular flower menu.")
        print(f"Error: Flower '{flower_name}' already exists")  # Debugging statement
        return

    # Add new flower with the stock amount
    inventory["flower"]["regular"][flower_name] = {
        "1.75": 10, "3.5": 20, "7": 30, "14": 50, "Stock": stock_amount
    }

    # Save the updated inventory to the file
    save_inventory()

    print(f"Flower '{flower_name}' added successfully with {stock_amount} grams")  # Debugging statement
    update.message.reply_text(f"✅ Added new flower '{flower_name}' with {stock_amount} grams in stock.")





# Function to remove a regular flower
def remove_flower(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 1:
        update.message.reply_text("📋 Usage: /remove_flower FlowerName\n\nExample: /remove_flower Wedding Cake 🎂")
        return

    flower_name_input = " ".join(context.args).strip()

    # Check if the flower exists in the regular category
    found_flower = None
    for flower_name in inventory["flower"]["regular"].keys():
        if flower_name == flower_name_input:
            found_flower = flower_name
            break

    if found_flower:
        # Remove the regular flower
        del inventory["flower"]["regular"][found_flower]

        # Save the updated inventory to the file
        save_inventory()

        update.message.reply_text(f"✅ Removed flower '{found_flower}' from the menu.")
    else:
        update.message.reply_text(f"❌ Flower '{flower_name_input}' not found in the regular flower menu.")

# Function to add an exotic flower with stock amount
def add_exotic(update: Update, context: CallbackContext) -> None:
    if len(context.args) != 2:
        update.message.reply_text("📋 Usage: /add_exotic ExoticName StockAmount\n\nExample: /add_exotic Gumdrop 50")
        return

    exotic_name, stock_amount = context.args[0], int(context.args[1])

    if exotic_name in inventory["flower"]["Exotic"]:
        update.message.reply_text(f"❌ Exotic flower '{exotic_name}' already exists in the exotic flower menu.")
        return

    # Add new exotic flower with the stock amount
    inventory["flower"]["Exotic"][exotic_name] = {
        "3.5": 25, "7": 50, "14": 100, "Stock": stock_amount
    }
    update.message.reply_text(f"✅ Added new exotic flower '{exotic_name}' with {stock_amount} grams in stock.")


# Function to remove an exotic flower
def remove_exotic(update: Update, context: CallbackContext) -> None:
    print("Received /remove_exotic command")  # Debugging statement

    if len(context.args) < 1:
        update.message.reply_text("📋 Usage: /remove_exotic ExoticName\n\nExample: /remove_exotic Gumdrop")
        print("Error: No exotic flower name provided")  # Debugging statement
        return

    exotic_name_input = " ".join(context.args).strip()  # Join all parts of the flower name

    print(f"Exotic flower name to remove: {exotic_name_input}")  # Debugging statement

    # Check if the flower exists in the exotic category
    found_exotic = None
    for exotic_name in inventory["flower"]["Exotic"].keys():
        if exotic_name == exotic_name_input:
            found_exotic = exotic_name
            break

    if found_exotic:
        # Remove the exotic flower
        del inventory["flower"]["Exotic"][found_exotic]

        # Save the updated inventory to the file
        save_inventory()

        print(f"Removed exotic flower '{found_exotic}' from the menu")  # Debugging statement
        update.message.reply_text(f"✅ Removed exotic flower '{found_exotic}' from the menu.")
    else:
        update.message.reply_text(f"❌ Exotic flower '{exotic_name_input}' not found in the exotic flower menu.")
        print(f"Error: Exotic flower '{exotic_name_input}' not found")  # Debugging statement


def edit_clockin(update: Update, context: CallbackContext) -> None:
    print("Entering the /edit_clockin command...")  # Trace command entry

    if len(context.args) < 3:
        update.message.reply_text(
            "📋 Usage: /edit_clockin FirstName LastName 'YYYY-MM-DD HH:MM:SS'\n\nExample: /edit_clockin John Doe '2024-09-07 09:00:00'")
        print("Error: Not enough arguments provided.")
        return

    # Capture the employee's name and the new clock-in time
    employee_name = " ".join(context.args[0:2])
    new_clockin_time_str = context.args[2]

    print(f"Employee Name: {employee_name}")  # Debugging statement
    print(f"New Clock-in Time (string): {new_clockin_time_str}")  # Debugging statement

    # Parse the provided datetime
    new_clockin_time = parse_date(new_clockin_time_str)

    if not new_clockin_time:
        update.message.reply_text("❌ Invalid date format. Please use 'YYYY-MM-DD HH:MM:SS'.")
        print("Error: Invalid date format.")
        return

    print(f"Parsed New Clock-in Time (datetime object): {new_clockin_time}")  # Debugging statement

    # Check if the employee exists in the clock_in_times
    if employee_name in clock_in_times:
        clock_in_times[employee_name] = new_clockin_time.strftime('%Y-%m-%d %H:%M:%S')
        print(f"Updated clock-in time for {employee_name}: {clock_in_times[employee_name]}")  # Debugging statement
        update.message.reply_text(f"✅ **{employee_name}'s** clock-in time has been updated to {new_clockin_time_str}.")
    else:
        update.message.reply_text(f"❌ **{employee_name}** has not clocked in.")
        print(f"Error: {employee_name} has not clocked in.")


# Function to handle /edit_clockout command
def edit_clockout(update: Update, context: CallbackContext) -> None:
    if len(context.args) < 3:
        update.message.reply_text("📋 Usage: /edit_clockout FirstName LastName 'YYYY-MM-DD HH:MM:SS'\n\nExample: /edit_clockout John Doe '2024-09-07 17:00:00'")
        return

    employee_name = " ".join(context.args[0:2])
    new_clockout_time_str = context.args[2]

    # Check if employee exists
    if employee_name not in employees:
        update.message.reply_text(f"❌ **{employee_name}** is not an employee. Please add them first.")
        return

    # Parse the provided datetime
    try:
        new_clockout_time = datetime.strptime(new_clockout_time_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        update.message.reply_text("❌ Invalid date format. Please use 'YYYY-MM-DD HH:MM:SS'.")
        return

    # Ensure the employee has clocked in before clocking out
    if employee_name not in clock_in_times:
        update.message.reply_text(f"❌ **{employee_name}** has not clocked in.")
        return

    # Calculate the time worked
    start_time = clock_in_times[employee_name]
    time_worked = new_clockout_time - start_time

    # Update the clock-out time and worked time
    worked_times[employee_name] = time_worked
    update.message.reply_text(f"✅ **{employee_name}'s** clock-out time has been updated to {new_clockout_time_str}. Total worked time: {time_worked}.")


from telegram.ext import ConversationHandler, MessageHandler, Filters

# Conversation states
ASKING_NAME, ASKING_ID = range(2)

def start(update: Update, context: CallbackContext) -> None:
    # Check if the user accessed the bot via a specific argument (like 'welcome')
    if context.args and context.args[0] == 'welcome':
        # Display the welcome message and prompt the user to join the rewards program
        message = ("👋 Thank you for visiting T&D Treehouse 🌲\n\n"
                   "Click /join to sign up for our rewards program. "
                   "You'll get access to exclusive offers and discounts!")
        update.message.reply_text(message)
    else:
        # Standard start message
        update.message.reply_text("Welcome! Use /join to sign up for the rewards program.")

def join(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Welcome to the rewards program! Please enter your first and last name.")
    return ASKING_NAME

def ask_name(update: Update, context: CallbackContext) -> int:
    # Store the user's name in context
    full_name = update.message.text
    context.user_data["full_name"] = full_name
    update.message.reply_text("Thanks! Now, please create a 4-digit ID to identify yourself.")
    return ASKING_ID

def ask_id(update: Update, context: CallbackContext) -> int:
    user_id = update.message.text

    # Check if the ID is a valid 4-digit number and not a duplicate
    if len(user_id) != 4 or not user_id.isdigit():
        update.message.reply_text("Please enter a valid 4-digit number.")
        return ASKING_ID
    elif user_id in smokers:
        update.message.reply_text("This ID is already in use. Please choose a different 4-digit ID.")
        return ASKING_ID

    full_name = context.user_data["full_name"]

    # Store the smoker's information
    smokers[user_id] = {
        "name": full_name,
        "points": 0
    }

    # Save smokers to JSON after adding the new smoker
    save_smokers()

    update.message.reply_text(f"Thanks {full_name}! You’ve successfully joined the rewards program with ID: {user_id}")
    return ConversationHandler.END

def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("You’ve canceled the join process.")
    return ConversationHandler.END

def generate_qr(update: Update, context: CallbackContext) -> None:
    try:
        # The bot link with the /start command
        bot_link = "https://t.me/TDTreehousebot?start=welcome"

        # Generate the QR code
        img = qrcode.make(bot_link)

        # Save the QR code as an image file
        qr_file = "bot_qr_code.png"
        img.save(qr_file)

        # Send the QR code image to the user
        with open(qr_file, 'rb') as qr_image:
            update.message.reply_photo(photo=InputFile(qr_image), caption="Here is your QR code! Scan to join the rewards program.")

    except Exception as e:
        update.message.reply_text("Something went wrong while generating the QR code.")
        print(f"Error: {str(e)}")

def update_inventory(flower_name, quantity):
    # Logic to update inventory based on the sold quantity
    pass

def add_sale_record(flower_name, quantity, price):
    # Logic to add a sale record
    pass

# Error handler function
def error(update, context: CallbackContext):
    print(f"Update {update} caused error {context.error}")  # Log the error to console


# Assuming you have admin IDs already stored
admin_ids = [908551450, 5120023328]  # Example admin IDs, add yours


from datetime import datetime, timedelta

# Function to generate reports based on time range
def generate_report(update: Update, context: CallbackContext, report_type="daily"):
    try:
        with open(TRANSACTION_FILE, 'r') as file:
            transactions = json.load(file)
    except FileNotFoundError:
        update.message.reply_text("No transactions found.")
        return

    # Calculate the date range for the report
    now = datetime.now()
    if report_type == "daily":
        start_date = now - timedelta(days=1)
    elif report_type == "weekly":
        start_date = now - timedelta(weeks=1)
    elif report_type == "monthly":
        start_date = now - timedelta(days=30)
    elif report_type == "yearly":
        start_date = now - timedelta(days=365)
    else:
        update.message.reply_text("Invalid report type. Choose from daily, weekly, monthly, yearly.")
        return

    # Filter transactions based on the date range
    report_transactions = [
        t for t in transactions if datetime.strptime(t["date"], '%Y-%m-%d %H:%M:%S') >= start_date
    ]

    if not report_transactions:
        update.message.reply_text(f"No {report_type} transactions found.")
        return

    # Generate the report
    report_message = f"📊 **{report_type.capitalize()} Report**:\n\n"
    total_sales = 0
    total_refunds = 0

    for transaction in report_transactions:
        if transaction["type"] == "Sale":
            total_sales += transaction["price"]
        elif transaction["type"] == "Refund":
            total_refunds += transaction["price"]
        report_message += (f"{transaction['date']} - {transaction['type']} - {transaction['product']} "
                           f"({transaction['quantity']}g): ${transaction['price']} (Smoker: {transaction['smoker_name']})\n")

    report_message += f"\nTotal Sales: ${total_sales}\nTotal Refunds: ${total_refunds}"

    update.message.reply_text(report_message, parse_mode='Markdown')



def main() -> None:
    # Replace 'YOUR_TOKEN_HERE' with your actual bot token
    updater = Updater("7300412368:AAGGzDoEBDxrxz_1BfDOrB-9dd6SXSBvLBw", use_context=True)

    # Load smokers at startup
    load_smokers()
    load_employees()  # Load staff data
    load_inventory()  # Load the inventory from JSON at bot startup (removed the argument)

    dispatcher = updater.dispatcher  # Correctly assign the dispatcher here

    # Add command handlers
    dispatcher.add_handler(CommandHandler("Start", start))
    dispatcher.add_handler(CommandHandler("add_employee", add_employee))
    dispatcher.add_handler(CommandHandler("remove_employee", remove_employee))
    dispatcher.add_handler(CommandHandler("Clock_in", clock_in))
    dispatcher.add_handler(CommandHandler("Clock_out", clock_out))
    dispatcher.add_handler(CommandHandler("view_staff", view_staff))
    dispatcher.add_handler(CommandHandler("menu", menu))
    dispatcher.add_handler(CommandHandler("sell", sell_product))
    dispatcher.add_handler(CommandHandler("add_smoker", add_smoker))
    dispatcher.add_handler(CommandHandler("remove_smoker", remove_smoker))
    dispatcher.add_handler(CommandHandler("view_smokers", view_smokers))
    dispatcher.add_handler(CommandHandler("view_points", view_points))
    dispatcher.add_handler(CommandHandler("redeem_points", redeem_points))
    dispatcher.add_handler(CommandHandler("add_inventory", add_inventory))
    dispatcher.add_handler(CommandHandler("check_inventory", check_inventory))
    dispatcher.add_handler(CommandHandler("add_flower", add_flower))
    dispatcher.add_handler(CommandHandler("remove_flower", remove_flower))
    dispatcher.add_handler(CommandHandler("add_exotic", add_exotic))
    dispatcher.add_handler(CommandHandler("remove_exotic", remove_exotic))
    dispatcher.add_handler(CommandHandler("edit_clockin", edit_clockin))
    dispatcher.add_handler(CommandHandler("edit_clockout", edit_clockout))
    dispatcher.add_handler(CommandHandler("generate_qr", generate_qr))
    dispatcher.add_handler(CommandHandler("generate_report", generate_report))
    dispatcher.add_handler(inventory_handler)
    dispatcher.add_handler(CommandHandler("cancel_inventory", cancel_inventory))
    dispatcher.add_handler(CommandHandler("refund", refund_product))
    dispatcher.add_handler(CommandHandler("view_inventory", view_inventory))
    dispatcher.add_handler(CommandHandler("reset_inventory", reset_inventory))
    dispatcher.add_error_handler(error)
    dispatcher.add_handler(CommandHandler("modify_points", modify_points))
    dispatcher.add_handler(CommandHandler("daily_report", lambda update, context: generate_report(update, context, "daily")))
    dispatcher.add_handler(CommandHandler("weekly_report", lambda update, context: generate_report(update, context, "weekly")))
    dispatcher.add_handler(CommandHandler("monthly_report", lambda update, context: generate_report(update, context, "monthly")))
    dispatcher.add_handler(CommandHandler("yearly_report", lambda update, context: generate_report(update, context, "yearly")))
    dispatcher.add_handler(CommandHandler("clear_transactions", clear_transactions))

    # Start the automatic inventory check for low stock notifications
    start_inventory_check(updater, 908551450)

    # Conversation handler for the /join command
    join_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("join", join)],
        states={
            ASKING_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_name)],
            ASKING_ID: [MessageHandler(Filters.text & ~Filters.command, ask_id)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    dispatcher.add_handler(join_conv_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
