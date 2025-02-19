from tkinter import *
import time
import csv_func, helper_func

# setting up root
root = Tk()
root.geometry("344x233")
root.minsize(800, 400)
root.maxsize(800, 750)
root.title("Se@rch: A Friendly Searching App")

# frame for displaying certain widget on certain area
top_frame = Frame(root)
top_frame.pack(side=TOP, fill=X)

textToSearch = Text(root, height=1, width=40)
# added listbox for displaying messages like a list on a box
listbox = Listbox(root, bg="light blue", fg="black", width=80, height=10, justify="center")
userInstruction = Label(root, text="Instructions:\n\n Step-1: Check the option then click on next \n\n Step-2: Enter the value or check your option \n\n Step-3: Click on search \n\n\n Done!! That's it\n", height=10)

searchInstruction = Label(root, text="", font=("Aria, 14"), pady=20)
errorMessage = Label(root, text="", fg="red", font=("Aria, 14"), pady=20)
resultAnswer = Label(root, text="")
searchResult = Label(root, text="")

statusBar = Label(root, text="")

# conditional dictionary; loop-up dictionary
showQuestion = {
    1: "Enter your subject/part-name below:", 
    2: "Enter your classmark below:", 
    3: "Enter your location below:", 
}

# checkbox options for search
selectedOption = StringVar()
option1 = Checkbutton(root, text="Will you be entering subject name/partname?", variable=selectedOption, onvalue="1", offvalue="", font=("Aria, 10"))
option2 = Checkbutton(root, text="Will you be entering classmark?", variable=selectedOption, onvalue="2", offvalue="", font=("Aria, 10"))
option3 = Checkbutton(root, text="Will you be entering location?", variable=selectedOption, onvalue="3", offvalue="", font=("Aria, 10"))

# checkbox options for locations
selectedLocation = StringVar()
locationOption1 = Checkbutton(root, text="Top floor bottom left", variable=selectedLocation, onvalue="1", offvalue="")
locationOption2 = Checkbutton(root, text="Top floor top left", variable=selectedLocation, onvalue="2", offvalue="")
locationOption3 = Checkbutton(root, text="Top floor top right", variable=selectedLocation, onvalue="3", offvalue="")
locationOption4 = Checkbutton(root, text="Top floor bottom right", variable=selectedLocation, onvalue="4", offvalue="")
locationOption5 = Checkbutton(root, text="Middle floor", variable=selectedLocation, onvalue="5", offvalue="")
locationOption6 = Checkbutton(root, text="Bottom floor", variable=selectedLocation, onvalue="6", offvalue="")

# reading of dats in CSV
location_and_classmark = csv_func.read_csv('classmark_location.csv') 
subject_and_classmark = csv_func.read_csv('subject_classmark.csv') 

# changing CSV values for usability purpose
findLocationByClassmark = helper_func.list_to_dictionary_csv(location_and_classmark)
findClassmarkBySubject = helper_func.list_to_dictionary_csv(subject_and_classmark)

# function to implement loader before any result
def wait_and_search(message):
    statusBar.pack()
    statusBar.config(text=f"{message}", pady=24, font=("Aria, 14"))
    statusBar.update()
    time.sleep(2)
    statusBar.config(text="Done")
    statusBar.pack_forget()

# function to change cursor to something more familiar for buttons
def change_cursor_on_buttons():
    tkinterButtons = [instructionButton, searchButton, showResultButton, mainPageButton, goBackButton ]
    for button in tkinterButtons:
        button.config(cursor="hand2")    

# function to hide every widgets before moving to different page
def hide_everything():
    mainMessage.pack_forget()
    searchInstruction.pack_forget()
    option1.pack_forget() 
    option2.pack_forget() 
    option3.pack_forget() 
    searchButton.pack_forget()
    instructionButton.pack_forget()
    errorMessage.pack_forget()
    textToSearch.pack_forget()
    locationOption1.pack_forget() 
    locationOption2.pack_forget() 
    locationOption3.pack_forget() 
    locationOption4.pack_forget() 
    locationOption5.pack_forget() 
    locationOption6.pack_forget() 
    showResultButton.pack_forget()
    goBackButton.pack_forget()
    userInstruction.pack_forget()
    listbox.pack_forget()
    mainPageButton.pack_forget()
    statusBar.pack_forget()
    searchResult.pack_forget()
     
# function to set widgets to show on start of a page
def show_start_page():
    textToSearch.delete('1.0', END)
    selectedLocation.set("")
    hide_everything()
    mainMessage.config(text="Hello User👋")
    mainMessage.pack()
    searchInstruction.config(text="Check the option of your choice \U0001F447")
    searchInstruction.pack()
    option1.pack(pady=(2,2)) 
    option2.pack(pady=(2,2)) 
    option3.pack(pady=(2,2)) 
    searchButton.pack(pady=(16, 0))
    instructionButton.pack(side=RIGHT, fill=BOTH)

# function to set widgets to show after user selects a option from first page
def show_second_page():
    errorMessage.pack_forget()
    if selectedOption.get():
        hide_everything()
        wait_and_search('loading....')
        question = showQuestion[int(selectedOption.get())]
        searchInstruction.config(text=f"{question}")
        
        # displaying checkbox option if location(option 3) is selected
        if selectedOption.get() == "3":         
            mainMessage.config(text="Your location options:\n")
            mainMessage.pack()
            locationOption1.pack(pady=(2,2)) 
            locationOption2.pack(pady=(2,2)) 
            locationOption3.pack(pady=(2,2)) 
            locationOption4.pack(pady=(2,2)) 
            locationOption5.pack(pady=(2,2)) 
            locationOption6.pack(pady=(2,2)) 
        else:
            # display of a input textbox for entering a value
            searchInstruction.pack()
            textToSearch.pack(pady=20)
        
        goBackButton.config(text="Go back")
        goBackButton.pack(side=BOTTOM, anchor=CENTER)
        showResultButton.pack(side=BOTTOM, anchor=CENTER)
        showResultButton.update()
    else:
        errorMessage.config(text="you need to input something before moving forward")
        errorMessage.pack(side=BOTTOM, anchor=CENTER)

# function to hide instruction then show the page 
def hide_instructions():
    hide_everything()
    if goBackButton.cget('text') != "previous page":
        show_start_page()
    else:
        show_second_page()

# function to show instruction on how to operate the app 
def show_instructions():
    hide_everything()
    userInstruction.pack()
    userInstruction.config(font=('Aria, 10'), pady=12)
    mainMessage.config(text="Are you ready to search now?\n")
    mainMessage.pack()
    mainPageButton.pack()
     
# option to show search result
def show_searches():
    errorMessage.pack_forget()
    if textToSearch.get("1.0", END).strip() or selectedLocation.get() != "":
        hide_everything()
        textReceived = textToSearch.get("1.0", END).strip()
        searchInstruction.config(text="Search Result:")
        wait_and_search("searching...")
        
        if ((textReceived != "" and textReceived != None) or selectedLocation.get() != ""): 
            mainMessage.config(text="Your search result:\n")
            mainMessage.pack()
            mainPageButton.pack(side=BOTTOM, anchor=CENTER)
            goBackButton.config(text="previous page")
            goBackButton.pack(side=BOTTOM, anchor=CENTER)
            
            """
                displaying output based on user's choice
            """
            if selectedOption.get() == "1":
                # passing props with values to display  
                propsDict = {
                    "searchResult":searchResult,
                    "listbox":listbox,
                    "end":END,
                    "findClassmarkBySubject":findClassmarkBySubject,
                    "findLocationByClassmark":findLocationByClassmark,
                    "textToSearch":textReceived
                }
                helper_func.render_subject(True, propsDict)
                               
            if selectedOption.get() == "2":
                # passing props with values to display  
                propsDict = {
                    "searchResult":searchResult,
                    "findClassmarkBySubject":findClassmarkBySubject,
                    "findLocationByClassmark":findLocationByClassmark,
                    "textToSearch":textReceived
                }
                helper_func.render_classname(True, propsDict)

            if selectedOption.get() == "3":   
                # passing props with values to display  
                propsDict = {
                    "searchResult":searchResult,
                    "listbox":listbox,
                    "end":END,
                    "findClassmarkBySubject":findClassmarkBySubject,
                    "findLocationByClassmark":findLocationByClassmark,
                    "selectedLocation":selectedLocation
                }
                helper_func.render_location(True, propsDict)
    else:
        # error handling by showing error message
        errorMessage.config(text="nothing to search")
        errorMessage.pack()
        
# creating button, adjusting its design, adding command for them
instructionButton = Button(top_frame, text="💡\n Click here for Instructions", font=("Arial", 10), command=show_instructions, background="yellow", fg="blue" ,relief="groove")
searchButton = Button(root, text="Next", command=show_second_page, padx=10, pady=10, background="blue", fg="white", borderwidth=0 ,relief="groove")
showResultButton = Button(root, text="Search", command=show_searches, padx=10, pady=10, background="blue", fg="white", borderwidth=0 ,relief="groove")
mainPageButton = Button(root, text="Go to Main Page", command=show_start_page, padx=10, pady=10, background="blue", fg="white", borderwidth=0 ,relief="groove")
goBackButton = Button(root, text="", command=hide_instructions, padx=10, pady=10, background="white", fg="blue", borderwidth=0 ,relief="groove")

# logo for the app with the help of a label
appLogo = Label(top_frame, text="Se@rch", font=("Arial", 14), fg="blue", background="white")
# label to display custom message based on pages  
mainMessage = Label(root, text="", font=("Aria, 16"), fg="black")

appLogo.pack(side=LEFT, fill=BOTH)
instructionButton.pack(side=RIGHT, fill=BOTH)

change_cursor_on_buttons()   
show_start_page()

root.mainloop()
