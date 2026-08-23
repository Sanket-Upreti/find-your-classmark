import csv_func, location_available
from engine import dataset, query
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

userOptions = ['subject name or part-name', 'classmark', 'location']

userOptionIndex = 0

# dynamically displaying options for user to select and start
for userOption in userOptions:
    userOptionIndex += 1
    print(f"{userOptionIndex}.", f"Enter a {userOption}") 
    
# function to display list of locations for users to select from 
def print_location_option():
    print("Please Select a NUMBER from all available locations:")   
    for key, value in location_available.location_options.items():
        print(f"{key}.", f"{value}")   
    
    # error handling when user's selection doesn't follow expectation
    inputToMatchInCSV = input_error_handling(int, f"Enter the {userOptions[2]}:")   
    return inputToMatchInCSV

# error handling with try...catch when choice isn't a number
userChoice = input_error_handling(int, "Your choice here:")

# making sure both CSV files exist, then loading them
csv_func.ensure_csv_files()
classmarkData = dataset.load_dataset()

if userChoice is not None:
    # error handling when the number typed isn't one of the options shown above
    if userChoice < 1 or userChoice > len(userOptions):
        print(f"----------Error: Please choose a number between 1 and {len(userOptions)}. Try from the beginning.-------")
    else:
        inputToMatchInCSV = ""
        if userChoice != 3:
            # displaying message with error handling for options to get subject and classname
            inputToMatchInCSV = input_error_handling(str, f"Enter the {userOptions[userChoice - 1]}:")
        else:
            # displaying location options for users to choose from
            inputToMatchInCSV = print_location_option()
         
        if inputToMatchInCSV is not None:
            """ 
                the engine works out the answer, then the renderer decides how to say it;
                every option follows the same two steps
            """
            if userChoice == 1:
                result = query.find_by_subject(classmarkData, inputToMatchInCSV)
                resultLines = text.subject_lines(result)
                   
            if userChoice == 2:
                result = query.find_by_classmark(classmarkData, inputToMatchInCSV)
                resultLines = text.classmark_lines(result)

            if userChoice == 3:  
                result = query.find_by_location(classmarkData, inputToMatchInCSV, location_available.location_options)
                resultLines = text.location_lines(result)

            for resultLine in resultLines:
                print(resultLine)
