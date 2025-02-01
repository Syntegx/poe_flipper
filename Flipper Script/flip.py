import re
import sys
import pyperclip
import time

def clear_clipboard():
    """
    Clears the clipboard by setting its content to an empty string.
    """
    pyperclip.copy('')

def monitor_clipboard():
    """
    Continuously monitors the clipboard for new content.
    When the content changes, it returns the new clipboard content.
    
    Returns:
        str: The new content of the clipboard.
    """
    last_clipboard_text = pyperclip.paste()  # Get the current clipboard content
    print('Waiting for new input...')
    while True:
        current_clipboard_text = pyperclip.paste()  # Get the updated clipboard content
        # Check if the clipboard content has changed
        if current_clipboard_text != last_clipboard_text:
            # If it has changed, return the new content
            return current_clipboard_text
        time.sleep(1)  # Wait before checking again

def extract_stats():
    """
    Extracts item stats (e.g., armor, weapon) from clipboard content.
    
    Returns:
        tuple: A tuple containing the extracted data and a tuple of booleans indicating the type of item.
            - data (list): List of extracted stats from clipboard content.
            - bools (tuple): Tuple of booleans indicating whether the item is Energy Shield, Body Armor, or a Weapon.
    """
    try:
        # Monitor clipboard for new data and clear it afterward
        data_block = monitor_clipboard()
        clear_clipboard()

        print(f"Extracted data block: {data_block}")
        
        # Split input data into sublists by spaces
        data = [line.strip().split() for line in data_block.split('\n') if line.strip()]
        
        # Check the type of item (Energy Shield, Body Armor, Weapon)
        esBool = any('Energy' in sublist for sublist in data)
        chestBool = any('Body' in sublist for sublist in data)
        martBool = any('Damage:' in sublist for sublist in data)  # Detect weapon damage attributes
        eleBool = any(damage_type in sublist for sublist in data for damage_type in ['Fire', 'Cold', 'Lightning', 'Elemental'])

        # Filter and process the data based on the type of item
        if esBool:
            # Process energy/shield-related data
            data = [
                data[index] for index, sublist in enumerate(data)
                if ('Energy' in sublist and 'Shield' in sublist or 'Shield:' in sublist)
                and 'Recharge' not in sublist and 'maximum' not in sublist
            ]
        elif martBool:
            # Process weapon data (damage-related)
            if eleBool:
                data = [
                    data[index] for index, sublist in enumerate(data)
                    if ('Damage:' in sublist) or 'Attacks' in sublist or 'increased' in sublist and not 'Adds' in sublist
                ]
            else:
                data = [
                    data[index] for index, sublist in enumerate(data)
                    if ('Damage:' in sublist and 'Physical' in sublist) or 'Attacks' in sublist or 'increased' in sublist and not 'Adds' in sublist
                ]
        else:
            # Process armor-related data (e.g., evasion)
            data = [
                data[index] for index, sublist in enumerate(data)
                if 'Evasion' in sublist and not 'to' in sublist
            ]
        
        # Return the extracted data along with item type booleans
        bools = esBool, chestBool, martBool, eleBool
        return data, bools
    except KeyboardInterrupt:
        print('Program exited by user.')
        sys.exit(0)

def extract_armor(sublist):
    """
    Extracts numerical armor-related stats from a list of strings.
    
    Args:
        sublist (list): The list containing armor stats.
        
    Returns:
        list: A list of extracted numerical values related to armor stats.
    """
    numbers = [] 
    for item in sublist:
        # Extract digits for normal numbers
        item = str(item)
        if re.search(r'\d', item):
            number = re.sub(r'\D', '', item)  # Remove non-digit characters
            if re.search(r'%', item):
                # Convert percentage to decimal
                numbers.append(int(number) / 100)
            else:
                # Append the number as an integer
                numbers.append(int(number))
    return numbers

def extract_weapon(sublist):
    """
    Extracts weapon-related stats (physical damage, elemental damage, and speed) from a list of strings.
    
    Args:
        sublist (list): The list containing weapon stats.
        
    Returns:
        dict: A dictionary containing 'physical', 'elemental', and 'speed' stats as lists.
    """
    numbers = {
        'physical': [],
        'elemental': [],
        'speed': []
    }

    for item in sublist:
        item = str(item)
        if re.search(r'\d', item):
            if 'Elemental' in item and '-' in item:
                # Extract and average the elemental damage range
                ranges = re.findall(r'(\d+-\d+)', item)
                mean = 0
                for range in ranges:
                    start, end = map(int, range.split('-'))
                    mean += (start + end) / 2
                numbers['elemental'].append(mean)
            else:
                number = re.sub(r'[^\d-]', '', item)  # Remove non-digit characters
                if re.search(r'%', item):
                    if 'Physical' in item:
                        numbers['physical'].append(int(number) / 100)
                elif '-' in item:
                    # Handle the range case and calculate the average
                    start, end = map(int, number.split('-'))
                    mean = (start + end) / 2
                    if 'Damage' in item and 'Physical' in item:
                        numbers['physical'].append(mean)
                    elif 'Damage' in item and any(d in item for d in ['Fire', 'Cold', 'Lightning']):
                        numbers['elemental'].append(mean)
                elif 'Second:' in item:
                    numbers['speed'].append(int(number) / 100)

    # Return the extracted stats, default to zero if none found
    if not numbers:
        return [0]
    return numbers

def flippid_armor(numbers, check):
    """
    Calculates the expected result for an armor item based on the extracted stats.
    
    Args:
        numbers (list): A list of numerical values related to armor.
        check (bool): A flag indicating the type of armor (True for specific armor, False for general).
        
    Returns:
        float: The calculated armor result.
    """
    fac = 0.4 if check else 0.2
    base, increase = numbers if len(numbers) == 2 else (numbers[0], 0)
    return (base / (increase + 1)) * (increase + 1 + fac) * 1.2

def flippid_mart(numbers):
    """
    Calculates the expected DPS (Damage per Second) for a weapon based on extracted stats.
    
    Args:
        numbers (dict): A dictionary containing 'physical', 'elemental', and 'speed' stats.
        
    Returns:
        tuple: A tuple containing physical DPS, elemental DPS, and total DPS.
    """
    ele = sum(numbers['elemental']) if numbers['elemental'] else 0
    atk = numbers['speed'][0]
    increase = numbers['physical'][1] if len(numbers['physical']) > 1 else 0
    dmg = numbers['physical'][0]
    edps = ele * atk
    pdps = (dmg / (increase + 1)) * (increase + 1 + 0.4) * 1.2 * atk
    tot = edps + pdps
    return pdps, edps, tot

def main():
    """
    The main loop of the program. Continuously extracts data from the clipboard,
    processes it, and outputs the expected result based on the type of item (armor, weapon).
    """
    while True:  # Loop to keep asking for input
        try:
            data, checks = extract_stats()
            print(data)
            esBool, chestBool, martBool, eleBool = checks
            
            if data is None:  # If exit command was given
                print("Exiting program.")
                break
            
            # Determine the item type and process accordingly
            if martBool:
                extracted_numbers = extract_weapon(data)
                phys, ele, tot = flippid_mart(extracted_numbers)  # Use weapon calculation
                print(f'Expected result DPS: {tot}  eDPS: {ele}  pDPS: {phys}')
            elif chestBool:
                extracted_numbers = extract_armor(data)
                print(extracted_numbers)
                result = flippid_armor(extracted_numbers, check=True)  # Use armor calculation
                print(f'Expected result (Chest): {result}')
            else:
                extracted_numbers = extract_armor(data)
                print(extracted_numbers)
                result = flippid_armor(extracted_numbers, check=False)  # Use general armor calculation
                print(f'Expected result (Other): {result}')
            print('\n----------------------------------------------------------------------------\n')
        except Exception as e:
            print(f'An error occurred: {e}')

if __name__ == '__main__':
    print('Please be advised that this script continuously reads the content of your clipboard.')
    print('After reading the content, your clipboard will immediatly be purged which leads to not beeing able to copy paste stuff.')
    print('To start please copy (CTRL - C) some stats from the POE2 Trade site.')
    main()
