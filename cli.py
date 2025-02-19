import csv_func, helper_func, location_available

print('''------------------Hello There!!----------------------
We'll be providing you your classmark together with its locations and subject name(s)
-------------------------------------------------------
Please select one of the option below by typing your desired option number''')

userOptions = ['subject name or part-name', 'classmark', 'location']

userOptionIndex = 0;

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
    inputToMatchInCSV = helper_func.input_error_handling(int, f"Enter the {userOptions[userChoice - 1]}:")   
    return inputToMatchInCSV

# error handling with try...catch when choice isn't a number
userChoice = helper_func.input_error_handling(int, "Your choice here:")
    
# reading CSV for its values
location_and_classmark = csv_func.read_csv('classmark_location.csv') 
subject_and_classmark = csv_func.read_csv('subject_classmark.csv') 

findLocationByClassmark = helper_func.list_to_dictionary_csv(location_and_classmark)
findClassmarkBySubject = helper_func.list_to_dictionary_csv(subject_and_classmark)

if userChoice != "null" and userChoice != None:
    inputToMatchInCSV = ""
    if userChoice != 3:
        # displaying message with error handling for options to get subject and classname
        inputToMatchInCSV = helper_func.input_error_handling(str, f"Enter the {userOptions[userChoice - 1]}:")
    else:
        # displaying location options for users to choose from
        inputToMatchInCSV = print_location_option()
     
    if inputToMatchInCSV != "null" and inputToMatchInCSV != None:
        # reusuable dictionary for any user's choice
        render_props = {
            "findClassmarkBySubject": findClassmarkBySubject,
            "findLocationByClassmark": findLocationByClassmark,
            "textToSearch": inputToMatchInCSV
        }
        if userChoice == 1:
            propsDict = render_props
            helper_func.render_subject(False, propsDict)
               
        if userChoice == 2:
            propsDict = render_props
            helper_func.render_classname(False, propsDict)

        if userChoice == 3:  
            propsDict = render_props
            helper_func.render_location(False, propsDict)
    
