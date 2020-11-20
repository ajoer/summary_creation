# Summary Creation

This repository holds the code and data for the Summary Creation data collection project (2020).
In the project, we create a dataset of user generated summaries where demographic information (gender, race and age) of the summary author is included in the metadata. The dataset is meant so enable studies in bias, demographic factors and fairness in summarization systems and function similarly as the TrustPilot corpus for sentiment analysis studies. 

We collect the data using Mechanical Turk and use texts (biographies) extracted from Wikipedia using the [Wikidata API](https://query.wikidata.org/).

We will conduct post-processing of the user generated summaries.

## Repository structure

The repository is structured as follows. There are two top directories, **data** and **code** . 

In the *data* directory, all data used in this project is contained, all code used in the project is in the **code** directory.

### **Data**

The Data directory contains data related to the Mechanical Turk study as well as the output data from the studies. 
NB: The input for the MTurk template is located in the [Summary Preferences repository](https://github.com/ajoer/summary_preferences) in the directory data/mturk/input.

#### */mturk* 
*/mturk* contains one directory, */output*, as well as two files containing the setup for the MTurk experiments, the summary_quality_metadata and summary_quality_template.

* The output subdirectory contains the raw data files from the Mechanical Turk experiments as well as the reviewed data file. This latter is used for analyses and is also uploaded to MTurk to approve and reject assignments. The raw output data from Mechanical Turk is only used to approve and reject assignments. 

### **Code**

The Code directory contains a script for approving and analysing MTurk output data.

Once the Mechanical Turk data is in (data/mturk/output/raw), the following script is used for assignment approval/rejection.

* mturk_results_approve reads in the raw MTurk data and outputs the same csv file with data for approval and rejections along with reasons for rejections.