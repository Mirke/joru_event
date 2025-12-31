# Bun Dictionary

## DESCRIPTION

Python software that allows you to add in JSON files and filter and grab chat messages. Left side panel has the words in the JSON file/s and right side will show the comments that the word exists in.

## STEP BY STEP INSTALL

1. If needed — Install Python 3.4 or higher remember.
2. When installing remember to check in "Add Python [version number] to PATH
3. Open terminal software of choice
4. Run ```pip --version``` to check if you have it installed.
5. Run ```pip install PyQt6```
6. Now you can either double click on app.py or move in terminal to folder and run ```py .\app.py``` for windows and ```py app.py``` for linux

## FEATURES

* **Load JSON**  — If you have a Twitch chat JSON file you can load in the file into the software (I mean that is the reason for this software)
* **Load Folder** — Able to load in a folder that contains JSON files and load in all of them into the application.
* **Saved Words** — Words that you double-click in the left side box gets added here and you can add in own and remove them.
* **Nouns** — Filters so only nouns that exists in a certain game is shown.
* **Adjectives** — Filters so only adjectives that exists in a certain game is shown.
* **Hide username** — When a word is selected and "hide username" is checked, then the name won't be in the comment hiding them.
* Sort by **alphabetical** or **count** words — This sorts the words by these two properties in the left panel.
* **Search bar**  — which allows for searching for a specific word in the left panel.
* **Quick access** — double tapping 'Caps lock' button will show you number options of selecting a part of the program, like search bar etc.
* **ESC-button** deselects everything (Might remove this because caps-lock might be well)

## FILES

* _blacklist.txt_ counts out the users in the JSON files.
* _saved_words.txt_ contains the saved words as a save option.

