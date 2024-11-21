# PublicationsRetriever

## CI Workflows
### Github Actions
[Maven CI](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/maven.yml): ![Build Status](https://github.com/LSmyrnaios/PublicationsRetriever/workflows/Java%20CI%20with%20Maven/badge.svg?branch=master)<br>
[CodeQL](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/codeql-analysis.yml): [![CodeQL](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/codeql-analysis.yml/badge.svg?branch=master)](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/codeql-analysis.yml)<br>
[Github pages](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/pages/pages-build-deployment): [![pages-build-deployment](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/pages/pages-build-deployment/badge.svg?branch=master)](https://github.com/LSmyrnaios/PublicationsRetriever/actions/workflows/pages/pages-build-deployment)
### [Jenkins](https://jenkins-dnet.d4science.org/job/PublicationsRetriever/): [![Build Status](https://jenkins-dnet.d4science.org/buildStatus/icon?job=PublicationsRetriever)](https://jenkins-dnet.d4science.org/job/PublicationsRetriever/)
### [Nexus Maven Repository](https://maven.d4science.org/nexus/content/repositories/dnet45-snapshots/eu/openaire/publications_retriever/)
<br>

## Description & basic information

A Java-program which retrieves the Document and Dataset Urls from the given Publication-Web-Pages and if wanted, it can also download the full-texts and/or upload them to an **S3 Object Store**.<br>
Afterwards, these full-text documents are mined (by other pieces of software), in order to enrich a much more complete set of OpenAIRE publications with inference links, in the [**OpenAIRE Graph**](https://graph.openaire.eu/).<br>

This program is used either as a stand-alone download-tool for full-texts and datasets, or as a library for the [UrlsWorker](https://code-repo.d4science.org/lsmyrnaios/UrlsWorker)'s code, of OpenAIRE's "**PDF Aggregation Service**". <br>

The **PublicationsRetriever** takes as input the PubPages with their IDs -in JSON format- and gives an output -also in JSON format,
which contains the IDs, the PubPages, the Document or Dataset Urls, a series of informative booleans, the *MD5* "fileHash", the "fileSize" and a "comment".<br>
The "booleans" are:
- "wasUrlChecked": it signals whether the url was checked
- "wasUrlValid": it signals whether the url was a valid url (one that can be connected)
- "wasDocumentOrDatasetAccessible": it signals whether the url gave a document or dataset url
- "wasDirectLink": it signals whether the url was a document or dataset link itself
- "couldRetry": it signals whether it could be worth to check the url in the future (in case the sourceUrl gave the docOrDatasetUrl or it resulted in an error which might be eliminated in the future, like a "ConnectionTimeout")
<br>

Note: the values to the above "booleans" are Strings: "true", "false" or "N/A". 
<br>

The "comment" can have the following values:
- an empty string, if the document url is retrieved, and the user specified that the document files will not be downloaded
- the information if the resulted url is a dataset url
- the DocFileFullPath, if we have chosen to download the DocFiles
- the ErrorCause, if there was any error which prevented the discovery of the DocOrDatasetUrl (in that case, the DocOrDatasetUrl is set to "unreachable")
<br>

Sample JSON-input:
```
{"id":"dedup_wf_001::83872a151fd78b045e62275ca626ec94","url":"https://zenodo.org/record/884160"}
```
Sample JSON-output (with downloading of the full-texts):
```
{"id":"dedup_wf_001::83872a151fd78b045e62275ca626ec94","sourceUrl":"https://zenodo.org/record/884160","docUrl":"https://zenodo.org/record/884160/files/Data_for_Policy_2017_paper_55.pdf","wasUrlChecked":"true","wasUrlValid":"true","wasDocumentOrDatasetAccessible":"true","wasDirectLink":"false","couldRetry":"true","fileHash":"4e38a82fe1182e62b1c752b50f5ea59b","fileSize":"263917","comment":"/home/lampros/PublicationsRetriever/target/../example/sample_output/DocFiles/dedup_wf_001::83872a151fd78b045e62275ca626ec94.pdf"}
```
<br>

Explanation of some keywords: <br>
PubPage: *the web page with the publication's information.*<br> 
DocUrl: *the url of the fulltext-document-file.*<br>
DatasetUrl: *the url of the dataset-file.*<br>
DocOrDatasetUrl: *the url of the document or the dataset file.*<br>
Full-text: *the document containing all the text of a publication.*<br>
DocFileFullPath: *the full-storage-path of the fulltext-document-file.*<br>
ErrorCause: *the cause of the failure of retrieving the docUrl or the docFile.*<br>
<br>

The program's execution process can be found [here](documentation/program-execution-process.md).
<br>
This program utilizes multiple threads to speed up the process, while using politeness-delays between same-domain connections, in order to avoid overloading the data-providers.
<br>
In case no IDs are available to be used in the input, the user should provide a file containing just urls (one url per line)
and specify that wishes to process a data-set with no IDs, by changing the "**util.url.LoaderAndChecker.useIdUrlPairs**"-variable to "*false*".
<br>
If you want to run it with distributed execution on multiple VMs, you may give a different starting-number for the docFiles in each instance (see the run-instructions below).<br>
<br>

**Disclaimers**:
- Keep in mind that it's best to run the program for a small set of urls (a few hundred maybe) at first,
    in order to see which parameters work best for you (url-timeouts, domainsBlocking ect.).
- Please note that **PublicationsRetriever** is currently in **beta**, so you may encounter some issues.<br>
<br>

## Install & Run (using MAVEN)
To install the application, navigate to the directory of the project, where the ***pom.xml*** is located.<br>
Then enter this command in the terminal:<br>
**``mvn clean install``**<br>

To run the application you should navigate to the ***target*** directory, which will be created by *MAVEN* and run the executable ***JAR*** file,
while choosing the appropriate run-command.<br> 

**Run with standard input/output:**<br>
**``java -jar publications_retriever-1.1-SNAPSHOT.jar arg1:'-inputFileFullPath' arg2:<inputFile> arg3:'-retrieveDataType' arg4:'<dataType: document | dataset | all>' arg5:'-downloadDocFiles' arg6:'-docFileNameType' arg7:'idName' arg8:'-firstDocFileNum' arg9:'NUM' arg10:'-docFilesStorage'
arg11:'storageDir' < stdIn:'inputJsonFile' > stdOut:'outputJsonFile'``**<br>

**Run tests with custom input/output:**
- Inside ***pom.xml***, change the **mainClass** of **maven-shade-plugin** from "**PublicationsRetriever**" to "**TestNonStandardInputOutput**".
- Inside ***src/test/.../TestNonStandardInputOutput.java***, give the wanted testInput and testOutput files.<br>
- If you want to provide a *.tsv* or a *.csv* file with a title in its column,
    you can specify it in the **util.file.FileUtils.skipFirstRow**-variable, in order for the first-row (headers) to be ignored.
- If you want to see the logging-messages in the *Console*, open the ***resources/logback.xml***
    and change the ***appender-ref***, from ***File*** to ***Console***.<br>
- Run ``mvn clean install`` to create the new ***JAR*** file.<br>
- Execute the program with the following command:<br>
**``java -jar publications_retriever-1.1-SNAPSHOT.jar arg2:'<dataType: document | dataset | all>' arg3:'-downloadDocFiles' arg4:'-docFileNameType' arg5:'numberName' arg6:'-firstDocFileNum' arg7:'NUM' arg8:'-docFilesStorage' arg9:'storageDir' arg10:'-inputDataUrl' arg11: 'inputUrl' arg12: '-numOfThreads' arg13: <NUM>``**
<br><br>
*You can use the argument '-inputFileFullPath' to define the inputFile, instead of the stdin-redirection. That way, the progress percentage will appear in the logging file.*
<br><br>

**Arguments explanation:**
- **-retrieveDataType** and **dataType** will tell the program to retrieve the urls of type "*document*", "*dataset*" or "*all*"-dataTypes.
- **-downloadDocFiles** will tell the program to download the DocFiles.
    The absence of this argument will cause the program to NOT download the docFiles, but just to find the *DocUrls* instead.
    Either way the DocUrls will be written to the JsonOutputFile.
- **-docFileNameType** and **< fileNameType >** will tell the program which fileName-type to use (*originalName, idName, numberName*).
- **-firstDocFileNum** and **< NUM >** will tell the program to use numbers as *DocFileNames* and the first *DocFile* will have the given number "*NUM*".
    The absence of this argument-group will cause the program to use the original-docFileNames.
- **-docFilesStorage** and **storageDir** will tell the program to use the given DocFiles-*storageDir*.
    If the *storageDir* is equal to **"S3ObjectStore"** , then the program uploads the DocFiles to an S3 storage (see the **note** below).
    The absence of this argument will cause the program to use a pre-defined storageDir which is: "*./docFiles*".
- **-inputDataUrl** and **inputUrl** will tell the program to use the given *URL* to retrieve the inputFile, instead of having it locally stored and redirect the *Standard Input Stream*.
- **-numOfThreads** and **NUM** will tell the program to use *NUM* number of worker-threads.
<br><br>
  The order of the program's arguments matters only **per pair**. For example, the argument **'storageDir'**, has to be placed always after the **'-docFilesStorage''** argument.
  <br><br>

**Note**: In order to access the S3ObjectStore, you should provide the file *"S3_credentials.txt"*, inside the *working directory*, which must contain the *endpoint*, the *accessKey*, the *secretKey*, the *region* and the *bucket*, in that order, separated by commas.<br>
<br>


## Example
You can check the functionality of **PublicationsRetriever** by running an example.<br>
Type **`./runExample.sh`** in the terminal and hit `ENTER`.<br>
Then you can see the results in the ***example/sample_output*** directory.<br>
The above script will run the following commands:
- **`mvn clean install`**: Does a *clean install*.
- **`rm -rf example/sample_output/*`**: Removes any previous example-results.
- **``cd target &&
    java -jar publications_retriever-1.1-SNAPSHOT.jar -retrieveDataType document -downloadDocFiles -docFileNameType numberName -firstDocFileNum 1 -docFilesStorage ../example/sample_output/DocFiles
    < ../example/sample_input/sample_input.json > ../example/sample_output/sample_output.json``**<br>
    This command will run the program with "**../example/sample_input/sample_input.json**" as input
    and "**../example/sample_output/sample_output.json**" as the output.<br>
    The arguments used are:
    - **-retrieveDataType** and **document** will tell the program to retrieve the urls of type "*document*".
    - **-downloadDocFiles** which will tell the program to download the DocFiles.
    - **-docFileNameType numberName** which will tell the program to use numbers as the docFileNames.
    - **-firstDocFileNum 1** which will tell the program to use numbers as DocFileNames and the first DocFile will have the number <*1*>.
    - **-docFilesStorage ../example/sample_output/DocFiles** which will tell the program to use the custom DocFilesStorageDir: "*../example/sample_output/DocFiles*".
<br>

## Customizations
- You can set **File-related** customizations in ***[util.file.FileUtils.java](https://github.com/LSmyrnaios/PublicationsRetriever/blob/7a74ffb7bdade36d6ba94032e730c2bbcb5f7731/src/main/java/eu/openaire/publications_retriever/util/file/FileUtils.java)***.
- You can set **Connection-related** customizations in ***[util.url.HttpConnUtils.java](https://github.com/LSmyrnaios/PublicationsRetriever/blob/7a74ffb7bdade36d6ba94032e730c2bbcb5f7731/src/main/java/eu/openaire/publications_retriever/util/http/HttpConnUtils.java)*** and ***[util.url.ConnSupportUtils.java](https://github.com/LSmyrnaios/PublicationsRetriever/blob/7a74ffb7bdade36d6ba94032e730c2bbcb5f7731/src/main/java/eu/openaire/publications_retriever/util/http/ConnSupportUtils.java)***.
