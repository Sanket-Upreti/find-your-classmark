import location_available

# reusuable error handling function
def input_error_handling(dataType, inputMessage):
    errorMessage= "Error: Invalid value type. Try from the beginning."
    # error handling for user choice, , checking for value error 
    try:
        userChoice = dataType(input(inputMessage))
        return userChoice
    except ValueError:
        return print(f"----------{errorMessage}-------")   

#  reusuable function for changing list to dictionary
def list_to_dictionary_csv(csvData):
    changedCsv = {}
    for row in csvData:
        key = row[0].lower()
        value = row[1]
        changedCsv[key] = value
    return changedCsv    

# getting key by passing value from CSV dictionary
def get_key_by_value(csvDictionary, valueToSearch):
    keyByValue = None
    for key, value in csvDictionary.items():
        """ 
            checking if it is a list for looping the value; 
            as the value to search surely contains inside a list
        """
        if value.startswith("[") and value.endswith("]"):
            for val in eval(value):
                if val.lower() == valueToSearch:
                    keyByValue = key
            
        else:
            if value.lower() == valueToSearch:
                keyByValue = key
    
    return keyByValue

# getting classnames by passing location from a dictionary with CSV values
def get_classes_with_location(csvDictionary, locationToSearch):
    classesByLocation = []
    for key, value in csvDictionary.items():
        if value.lower() == locationToSearch:
            classesByLocation.append(key)
    
    return classesByLocation

""" 
    the functions that will follow now gets used on both GUI and non GUI work;  
    They reduce repetitiveness, and obviously the lines of code 
    They code is separated mostly by if..else for GUI and non GUI rendering 
"""

# function to render output(subjectname/partname) when user selects option 1 from the starting page
def render_subject(isGui, props):
    renderProps = {}
    # storing received props as an argument and storing it as a value in dictionary called 'renderProps' for reuse of its value
    if isGui:
        renderProps = {
            "searchResult":props['searchResult'], "listbox":props['listbox'], "end":props['end'], "findClassmarkBySubject":props['findClassmarkBySubject'], "findLocationByClassmark":props['findLocationByClassmark'], "textToSearch":props['textToSearch'] 
        }
    else:
        renderProps = {
            "findClassmarkBySubject": props['findClassmarkBySubject'], "findLocationByClassmark": props['findLocationByClassmark'], "textToSearch": props['textToSearch'] 
        }
                
    classmarkBySubject = renderProps['findClassmarkBySubject'].get(renderProps['textToSearch'].lower())
                
    if classmarkBySubject is None:
        if isGui:
            renderProps['searchResult'].pack()
            renderProps['searchResult'].config(text=f"Thank you for answering, but no class was found for subject {renderProps['textToSearch']}")                
        else:
            print(f"Thank you for answering, but no class or location was found for subject {renderProps['textToSearch']}") 
    else:
        if classmarkBySubject.startswith("[") and classmarkBySubject.endswith("]"):
            if isGui:
                renderProps['listbox'].delete(0, renderProps['end'])
                for val in eval(classmarkBySubject):
                    locationByClassmark = renderProps['findLocationByClassmark'].get(val.lower())                        
                    # error handling when value is none
                    if locationByClassmark is None:
                        renderProps['searchResult'].pack()
                        renderProps['searchResult'].config(text=f"No location was found for subject {val}")   
                    else:
                        # rendering output in a 'list' for GUI when output is not a single value
                        renderProps['listbox'].pack(pady=2)
                        renderProps['listbox'].config(font=("Arial, 12"))
                        renderProps['listbox'].insert(renderProps['end'], f"Subject {renderProps['textToSearch']} happens on class {val} which is located in {locationByClassmark}")                            
            else:
                print(f"Thank you for answering. There are multiple classes happening for Subject {renderProps['textToSearch']}")  
                for val in eval(classmarkBySubject):
                    locationByClassmark = renderProps['findLocationByClassmark'].get(val.lower())
                    if locationByClassmark is None:
                        print(f"No location was found for subject {val}")   
                    else:
                        print(f"Subject {renderProps['textToSearch']} happens on class {val} which is located in {locationByClassmark}")               
        else:
            locationByClassmark = renderProps['findLocationByClassmark'].get(classmarkBySubject.lower())
            if isGui:
                renderProps['searchResult'].pack()
                if locationByClassmark is None:
                    renderProps['searchResult'].config(text=f"Thank you for answering, but no location was found for subject {renderProps['textToSearch']}")  
                else:
                    renderProps['searchResult'].config(text=f"Thank you for answering, Subject {renderProps['textToSearch']} happens on class {classmarkBySubject} which is located in {locationByClassmark}")  
            else:
                if locationByClassmark is None:
                    print(f"Thank you for answering, but no location was found for subject {renderProps['textToSearch']}")   
                else:
                    print(f"Thank you for answering, Subject {renderProps['textToSearch']} happens on class {classmarkBySubject} which is located in {locationByClassmark}")                               
  
# function to render output(classname) when option 2 is selected from starting page
def render_classname(isGui, props):
    renderProps={}
    # storing received props as an argument and storing it as a value in dictionary called 'renderProps' for reuse of its value
    if isGui:
        renderProps = {
            "searchResult":props['searchResult'], "findClassmarkBySubject":props['findClassmarkBySubject'], "findLocationByClassmark":props['findLocationByClassmark'], "textToSearch":props['textToSearch'] 
        }
    else:
        renderProps = {
            "findClassmarkBySubject": props['findClassmarkBySubject'], "findLocationByClassmark": props['findLocationByClassmark'], "textToSearch": props['textToSearch'] 
        }
    locationByClassmark = renderProps['findLocationByClassmark'].get(renderProps['textToSearch'].lower())
    subjectByClassmark = get_key_by_value(renderProps['findClassmarkBySubject'], renderProps['textToSearch'].lower())

    # error handling when none value is received with the help of if...else
    if locationByClassmark is None:
        if isGui:
            renderProps['searchResult'].pack()
        if subjectByClassmark is None:
            if isGui:
                renderProps['searchResult'].config(text=f"Thank you for answering, but no location or subject was found for class {renderProps['textToSearch']}")                
            else:
                print(f"Thank you for answering, but no location or subject was found for class {renderProps['textToSearch']}")   
        else:
            if isGui:
                renderProps['searchResult'].config(text=f"Thank you for answering, but no location was found for class {renderProps['textToSearch']} which has {subjectByClassmark} running on it")                
            else:
                print(f"Thank you for answering, but no location was found for class {renderProps['textToSearch']} which has {subjectByClassmark} running on it")   
    else:
        if isGui:
            renderProps['searchResult'].pack()
            
        if subjectByClassmark is None: 
            if isGui:
                renderProps['searchResult'].config(text=f"Thank you for answering, but no subject was found for class {renderProps['textToSearch']} which is in {locationByClassmark}")   
            else:
                print(f"Thank you for answering, but no subject was found for class {renderProps['textToSearch']} which is in {locationByClassmark}")               
        else:
            if isGui:
                renderProps['searchResult'].config(text=f"Thank you for answering, Subject {subjectByClassmark} happens on class {renderProps['textToSearch']} which is located in {locationByClassmark}")
            else:
                print(f"Thank you for answering, Subject {subjectByClassmark} happens on class {renderProps['textToSearch']} which is located in {locationByClassmark}")
                
def render_location(isGui, props):
    renderProps={}
    locationSelected=""    
    if isGui:
        renderProps = {
            "searchResult":props['searchResult'], "listbox":props['listbox'], "end":props['end'], "findClassmarkBySubject":props['findClassmarkBySubject'], "findLocationByClassmark":props['findLocationByClassmark'], "selectedLocation":props['selectedLocation']
        }
        locationSelected = location_available.location_options[int(renderProps['selectedLocation'].get())]       
    else:
        renderProps = {
            "findClassmarkBySubject": props['findClassmarkBySubject'], "findLocationByClassmark": props['findLocationByClassmark'], "textToSearch": props['textToSearch']
        }
        locationSelected = location_available.location_options.get(renderProps['textToSearch'])  

    # error handling when none value is received with the help of if...else
    if locationSelected is not None:
        if isGui: 
            renderProps['searchResult'].pack()
        
        classMarkByLocation =  get_classes_with_location(renderProps['findLocationByClassmark'], locationSelected.lower())
        if len(classMarkByLocation) == 0:
            if isGui:
                renderProps['searchResult'].config(text=f"Thank you for answering, but no class, subject or location was found for your search {locationSelected}. Please make sure your location is similar to the options provided")                
            else:
                print(f"Thank you for answering, but no class, subject or location was found for your search {locationSelected}. Please make sure your location is similar to the options provided")
        else:
            if isGui:
                renderProps['searchResult'].config(text=f"Thank you for answering, There are some classes and subjects taught in location {locationSelected}.\n Scroll inside the list to check more search results")                
                renderProps['listbox'].delete(0, renderProps['end'])
                renderProps['listbox'].pack(pady=20)
            else:
                print(f"Thank you for answering, There are some classes and subjects taught in location {locationSelected}")
            for val in classMarkByLocation:
                # getting key from the value entered by the user
                subjectByClassmark = get_key_by_value(renderProps['findClassmarkBySubject'], val.lower())
                if subjectByClassmark is None:
                    if isGui:
                        # inserting message to display on 'list' when some value from large values don't have a subject
                        renderProps['listbox'].insert(renderProps['end'], f"No subject was found for class {val} in location {locationSelected}" )   
                    else:
                        print(f"No subject was found for class {val} in location {locationSelected}")
                else:
                    if isGui:
                        # inserting message to display on 'list' when some value from large values have a subject
                        renderProps['listbox'].insert(renderProps['end'], f"Subject {subjectByClassmark} happens on class {val} which is located in {locationSelected}" )   
                    else:
                        print(f"Subject {subjectByClassmark} happens on class {val} which is located in {locationSelected}")
    else:
        if isGui:
            renderProps['searchResult'].config(text=f"Thank you for answering, but no class, subject or location was found for your search {locationSelected}")   
        else:
            print(f"Thank you for answering, but no class, subject or location was found for your search {renderProps['textToSearch']}")