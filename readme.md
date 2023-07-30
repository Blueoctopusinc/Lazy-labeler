# Lazy Labeler
![img_1.png](img_1.png)
Lazy Labeler is a Python desktop application specifically designed to simplify manual data labeling tasks for machine learning projects. The tool was initially created for personal use, tailored to handle moderate-sized labeling tasks. However, it may also be useful for others who require a straightforward and effective data labeling tool.

The interactive interface of Lazy Labeler allows for swift and efficient labeling of data using pre-established classes. The application does have limitations in handling large numbers of labels due to constraints on the hotkey labeling feature.

While there are more comprehensive data labeling tools available, Lazy Labeler serves as a practical option for smaller, more manageable datasets. The development of Lazy Labeler has also provided valuable experience in working with PyQt6.

Please feel free to use and adapt Lazy Labeler to suit your data labeling needs.

To use the Lazy Labeler application, follow these steps:

### Installation

1. Clone the repository from GitHub:

```
git clone https://github.com/exampleuser/lazy-labeler.git
cd lazy-labeler
```

2. Create a new virtual environment (optional but recommended):

```
python -m venv venv
```

3. Activate the virtual environment:

- On Windows:

```
venv\Scripts\activate
```

- On macOS and Linux:

```
source venv/bin/activate
```

4. Install the required dependencies using `pip`:

```
pip install -r requirements.txt
```

### JSON Format for Synonyms

This project was originally for labelling data that had the shape of an object as the classes, you can provde synonyms for each class in a JSON file. 

The synonyms JSON file should be formatted as follows:

```json
{
    "Class 1": ["Synonym 1", "Synonym 2", "Synonym 3", ...],
    "Class 2": ["Synonym 1", "Synonym 2", "Synonym 3", ...],
    "Class 3": {"Class_3_subcategory":  ["Synonym 1", "Synonym 2", "Synonym 3", ...],
                "Class_3_subcategory_2":  ["Synonym 1", "Synonym 2", "Synonym 3", ...], ...},
}
```
In my example one class could be comprised of multiple subcategories, so I used a dictionary to represent this.
Each class should have an associated list of synonyms. The synonyms will be used during the labeling process to suggest labels to the user based on the TF-IDF similarity between the sample and the class synonyms.


## Technologies Used

The Lazy Labeler application is built using the following technologies:

- **Python**: The core programming language used for the application.
- **PyQt6**: A set of Python bindings for The Qt Company’s Qt application framework used to create the graphical user interface.
- **Pandas**: A Python library used for data manipulation and analysis. It is used to load, modify, and save the dataset in CSV format.
- **SQLite w/sqlAlchemy**: A lightweight disk-based database. To store, retrieve, and manipulate tasks.
- **Threading**: The application makes extensive use of QThreads for any blocking operations, such as loading and saving data and generating the TF-IDF vectors.
- **Sci-kit Learn**: A Python library used for machine learning. It is used to compute the TF-IDF vectors and cosine similarity between samples and class synonyms.
## TF-IDF and Text Labeling

TF-IDF (Term Frequency-Inverse Document Frequency) is a numerical statistic used in information retrieval to reflect how important a word is to a document in a corpus. It is used in the Lazy Labeler application to provide guidance to the user during the labeling process.

When labeling a sample, the application computes the cosine similarity between the TF-IDF vectors of the sample and a set of synonyms for each class. The class with the highest similarity is suggested to the user, helping to speed up the labeling process. 

This feature is especially useful when the number of classes is large and/or the distinctions between classes are subtle. The TF-IDF results are displayed in real-time as the user navigates through the samples.

### Labeling Process and Hotkeys

1. Start the Lazy Labeler application.

2. Create a new labeling task or continue an existing one. Specify the data file (in CSV format) containing the samples to label. Optionally, provide the labels file (in JSON format) with class synonyms.

3. Once you're in a labeling task, the application will present data samples one by one. For each sample, use the hotkeys (keyboard shortcuts) to select the appropriate label(s) based on the displayed classes:

   - Press the corresponding hotkey (e.g., 1, 2, 3) to select the class label. The key for each class key is noted on the button.
   - Press the spacebar to go to the next sample.
   - Click the save button to save any labels created.
   
4. The application will suggest labels based on the computed TF-IDF similarity between the sample and the class synonyms. These suggestions aim to speed up the labeling process.

5. As you navigate through samples and label them, the progress will be saved automatically every 10 minutes (autosave feature). Additionally, you can manually save your progress at any time.





### Running Tests

The Lazy Labeler application comes with a suite of unit tests to ensure the functionality of its core components. The tests are written using the `pytest` framework.

To run the tests, follow these steps:

1. Ensure you have activated your virtual environment and installed all dependencies as described in the Installation section.

2. Install the `pytest` and `pytest-qt` packages if you haven't already. `pytest` is the testing framework we use, while `pytest-qt` is a `pytest` plugin that provides fixtures to simplify the testing of PyQt6 applications.

```bash
pip install pytest pytest-qt
```

3. Navigate to the root directory of the project (where the `tests` directory is located).

4. Run the tests using the `pytest` command:

```bash
pytest tests/
```

`pytest` will automatically discover and run all test files in the `tests/` directory.

Note: If you have a different directory structure, replace `tests/` with the path to the directory that contains your test files.

If the tests are successful, you should see an output indicating the number of tests passed. If any tests fail, `pytest` will provide a detailed error report to help you diagnose and fix the issue.