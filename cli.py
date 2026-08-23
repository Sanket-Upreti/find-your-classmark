import sys

import csv_func
from engine import config, query
from render import text

# reusuable error handling function
def input_error_handling(dataType, inputMessage):
    errorMessage= "Error: Invalid value type. Try from the beginning."
    # error handling for user choice, , checking for value error 
    try:
        userChoice = dataType(input(inputMessage))
        return userChoice
    except ValueError:
        return print(f"----------{errorMessage}-------")   

print('''------------------Hello There!!----------------------
We'll be providing you your classmark together with its locations and subject name(s)
-------------------------------------------------------
Please select one of the option below by typing your desired option number''')

# a different dataset can be searched by naming its config: python3 cli.py datasets/other.yaml
if len(sys.argv) > 1:
    classmarkData = config.load_config(sys.argv[1])
else:
    # making sure the files exist, then loading the dataset this app ships with
    csv_func.ensure_csv_files()
    classmarkData = config.load_default()
userOptions = classmarkData.searches

userOptionIndex = 0

# dynamically displaying options for user to select and start
for userOption in userOptions:
    userOptionIndex += 1
    print(f"{userOptionIndex}.", f"Enter a {userOption.label}") 
    
# function to display the choices a search offers, for users to select from 
def print_choice_option(search):
    print("Please Select a NUMBER from all available locations:")   
    for key, value in search.numbered_choices().items():
        print(f"{key}.", f"{value}")   
    
    # error handling when user's selection doesn't follow expectation
    inputToMatchInCSV = input_error_handling(int, f"Enter the {search.label}:")   
    return inputToMatchInCSV

# error handling with try...catch when choice isn't a number
userChoice = input_error_handling(int, "Your choice here:")

if userChoice is not None:
    # error handling when the number typed isn't one of the options shown above
    if userChoice < 1 or userChoice > len(userOptions):
        print(f"----------Error: Please choose a number between 1 and {len(userOptions)}. Try from the beginning.-------")
    else:
        searchSelected = classmarkData.search_at(userChoice - 1)

        if searchSelected.choices:
            # displaying the numbered choices for users to pick from
            inputToMatchInCSV = print_choice_option(searchSelected)
        else:
            # displaying message with error handling for the searches that take typed text
            inputToMatchInCSV = input_error_handling(str, f"Enter the {searchSelected.label}:")
         
        if inputToMatchInCSV is not None:
            """ 
                the engine works out the answer, then the renderer decides how to say it;
                every search follows the same two steps
            """
            result = query.run(classmarkData, searchSelected, inputToMatchInCSV)
            for resultLine in text.lines_for(searchSelected, result):
                print(resultLine)
