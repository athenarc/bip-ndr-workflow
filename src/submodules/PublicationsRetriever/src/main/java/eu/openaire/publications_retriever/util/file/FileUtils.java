package eu.openaire.publications_retriever.util.file;

import ch.qos.logback.classic.LoggerContext;
import com.google.common.collect.HashMultimap;
import eu.openaire.publications_retriever.PublicationsRetriever;
import eu.openaire.publications_retriever.crawler.MachineLearning;
import eu.openaire.publications_retriever.exceptions.DocFileNotRetrievedException;
import eu.openaire.publications_retriever.util.http.ConnSupportUtils;
import eu.openaire.publications_retriever.util.url.DataToBeLogged;
import eu.openaire.publications_retriever.util.url.LoaderAndChecker;
import eu.openaire.publications_retriever.util.url.UrlUtils;
import org.apache.commons.io.FileDeleteStrategy;
import org.apache.commons.lang3.StringUtils;
import org.json.JSONException;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import javax.xml.bind.DatatypeConverter;
import java.io.*;
import java.net.HttpURLConnection;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.util.*;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.Lock;
import java.util.concurrent.locks.ReentrantLock;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static org.apache.commons.io.FileUtils.deleteDirectory;


/**
 * @author Lampros Smyrnaios
 */
public class FileUtils
{
	private static final Logger logger = LoggerFactory.getLogger(FileUtils.class);
	
	private static Scanner inputScanner = null;
	private static PrintStream printStream = null;
	
	public static long numOfLines = 0;	// Only the main thread accesses it.
	
	public static int jsonBatchSize = 3000;	// Do not set it as "final", since other apps using this program might want to set their own limit.

	private static StringBuilder stringToBeWritten = null;	// It will be assigned and pre-allocated only if the "WriteToFile()" method is called.
	// Other programs using this program as a library might not want to write the results in a file, but send them over the network.

	private static int fileIndex = 0;	// Index in the input file
	public static boolean skipFirstRow = false;	// Use this to skip the HeaderLine in a csv-kindOf-File.
	public static final String endOfLine = System.lineSeparator();
	public static int unretrievableInputLines = 0;	// For better statistics in the end.


	public static final List<DataToBeLogged> dataToBeLoggedList = Collections.synchronizedList(new ArrayList<>(jsonBatchSize));
	
	public static final HashMap<String, Integer> numbersOfDuplicateDocFileNames = new HashMap<>();	// Holds docFileNames with their duplicatesNum.
	// If we use the above without external synchronization, then the "ConcurrentHashMap" should be used instead.

	public static boolean shouldDownloadDocFiles = false;	// It will be set to "true" if the related command-line-argument is given.
	public static boolean shouldUploadFilesToS3 = false;	// Should we upload the files to S3 ObjectStore? Otherwise, they will be stored locally.
	public static boolean shouldDeleteOlderDocFiles = false;	// Should we delete any older stored docFiles? This is useful for testing.

	public enum DocFileNameType {
		originalName, idName, numberName
	}
	public static DocFileNameType docFileNameType = null;

	public static final boolean shouldLogFullPathName = true;	// Should we log, in the jasonOutputFile, the fullPathName or just the ending fileName?
	public static int numOfDocFile = 0;	// In the case that we don't care for original docFileNames, the fileNames are produced using an incremental system.
	public static final String workingDir = System.getProperty("user.dir") + File.separator;
	public static String storeDocFilesDir = workingDir + "docFiles" + File.separator;
	public static int unretrievableDocNamesNum = 0;	// Num of docFiles for which we were not able to retrieve their docName.
	public static final Pattern FILENAME_FROM_CONTENT_DISPOSITION_FILTER = Pattern.compile(".*filename[*]?=(?:.*[\"'])?([^\"^;]+)[\";]*.*");
	
	public static final int MAX_FILENAME_LENGTH = 250;	// TODO - Find a way to get the current-system's MAX-value.
	
	public static String fullInputFilePath = null;	// Used when the MLA is enabled, and we want to count the number of lines in the inputFile, in order to optimize the M.L.A.'s execution.

	public static int duplicateIdUrlEntries = 0;

	private static final String utf8Charset = StandardCharsets.UTF_8.toString();

	public static final Pattern EXTENSION_PATTERN = Pattern.compile("(\\.[^._-]+)$");


	public FileUtils(InputStream input, OutputStream output)
	{
		FileUtils.inputScanner = new Scanner(input, utf8Charset);
		
		if ( MachineLearning.useMLA ) {	// In case we are using the MLA, go get the numOfLines to be used.
			if ( numOfLines == 0 ) {	// If the inputFile was not given as an argument, but as the stdin, instead.
				numOfLines = getInputNumOfLines();
				logger.debug("Num of lines in the inputFile: " + numOfLines);
			}
		}

		setOutput(output);

		if ( shouldUploadFilesToS3 )
			new S3ObjectStore();
	}


	public static void setOutput(OutputStream output)
	{
		try {
			FileUtils.printStream = new PrintStream(output, false, utf8Charset);
		}
		catch ( Exception e ) {
			logger.error(e.getMessage(), e);
			System.exit(20);
		}

		if ( shouldDownloadDocFiles )
			handleStoreDocFileDirectory();
	}


	public static void handleStoreDocFileDirectory()
	{
		File dir = new File(storeDocFilesDir);
		if ( shouldDeleteOlderDocFiles ) {
			logger.info("Deleting old docFiles..");
			try {
				deleteDirectory(dir);	// org.apache.commons.io.FileUtils
			} catch (IOException ioe) {
				logger.error("The following directory could not be deleted: " + storeDocFilesDir, ioe);
				FileUtils.shouldDownloadDocFiles = false;	// Continue without downloading the docFiles, just create the jsonOutput.
				return;
			} catch (IllegalArgumentException iae) {
				logger.error("This directory does not exist: " + storeDocFilesDir + "\n" + iae.getMessage());
				return;
			}
		}

		// If the directory doesn't exist, try to (re)create it.
		try {
			if ( !dir.exists() ) {
				if ( !dir.mkdirs() ) {	// Try to create the directory(-ies) if they don't exist. If they exist OR if sth went wrong, the result is the same: "false".
					String errorMessage;
					if ( PublicationsRetriever.docFilesStorageGivenByUser )
						errorMessage = "Problem when creating the \"storeDocFilesDir\": \"" + FileUtils.storeDocFilesDir + "\"."
								+ "\nPlease give a valid Directory-path.";
					else	// User has left the storageDir to be the default one.
						errorMessage = "Problem when creating the default \"storeDocFilesDir\": \"" + FileUtils.storeDocFilesDir + "\"."
								+ "\nPlease verify you have the necessary privileges in the directory you are running the program from or specify the directory you want to save the files to."
								+ "\nIf the above is not an option, then you can set to retrieve just the " + PublicationsRetriever.targetUrlType + "s and download the full-texts later (on your own).";
					System.err.println(errorMessage);
					logger.error(errorMessage);
					FileUtils.closeIO();
					System.exit(-3);
				}
			}
		} catch (SecurityException se) {
			logger.error(se.getMessage(), se);
			logger.warn("There was an error creating the docFiles-storageDir! Continuing without downloading the docFiles, while creating the jsonOutput with the docUrls.");
			FileUtils.shouldDownloadDocFiles = false;
		}
	}

	
	public static long getInputNumOfLines()
	{
		long lineCount = 0;
		
		// Create a new file to write the input-data.
		// Since the input-stream is not reusable.. we cant count the line AND use the data..
		// (the data will be consumed and the program will exit with error since no data will be read from the inputFile).
		String baseFileName = workingDir + "inputFile";
		String extension;
		if ( LoaderAndChecker.useIdUrlPairs )
			extension = ".json";
		else
			extension = ".csv";	// This is just a guess, it may be a ".tsv" as well or sth else. There is no way to know what type of file was assigned in the "System.in".
		
		// Make sure we create a new distinct file which will not replace any other existing file. This new file will get deleted in the end.
		int fileNum = 1;
		fullInputFilePath = baseFileName + extension;
		File file = new File(fullInputFilePath);
		while ( file.exists() ) {
			fullInputFilePath = baseFileName + (fileNum++) + extension;
			file = new File(fullInputFilePath);
		}
		
		try {
			printStream = new PrintStream(Files.newOutputStream(file.toPath()), false, utf8Charset);
			
			while ( inputScanner.hasNextLine() ) {
				printStream.print(inputScanner.nextLine());
				printStream.print(endOfLine);
				lineCount ++;
			}
			
			printStream.close();
			inputScanner.close();
			
			// Assign the new input-file from which the data will be read for the rest of the program's execution.
			inputScanner = new Scanner(Files.newInputStream(Paths.get(fullInputFilePath)));
		} catch (Exception e) {
			logger.error("", e);
			FileUtils.closeIO();
			System.exit(-10);	// The inputFile (stream) is already partly-consumed, no point to continue.
		}
		
		if ( FileUtils.skipFirstRow && (lineCount != 0) )
			return (lineCount -1);
		else
			return lineCount;
	}
	
	
	/**
	 * This method returns the number of (non-heading, non-empty) lines we have read from the inputFile.
	 * @return loadedUrls
	 */
	public static int getCurrentlyLoadedUrls()	// In the end, it gives the total number of urls we have processed.
	{
		if ( FileUtils.skipFirstRow )
			return FileUtils.fileIndex - FileUtils.unretrievableInputLines -1; // -1 to exclude the first line
		else
			return FileUtils.fileIndex - FileUtils.unretrievableInputLines;
	}


	private static final int expectedPathsPerID = 5;
	private static final int expectedIDsPerBatch = (jsonBatchSize / expectedPathsPerID);

	private static HashMultimap<String, String> idAndUrlMappedInput = null;	// This is used only be the main Thread, so no synchronization is needed.
	// This will be initialized and pre-allocated the 1st time it is needed.
	// When PublicationsRetriever is used as a library by a service, this functionality may not be needed.

	/**
	 * This method parses a Json file and extracts the urls, along with the IDs.
	 * @return HashMultimap<String, String>
	 */
	public static HashMultimap<String, String> getNextIdUrlPairBatchFromJson()
	{
		IdUrlTuple inputIdUrlTuple;

		if ( idAndUrlMappedInput == null )	// Create this HashMultimap the first time it is needed.
			idAndUrlMappedInput = HashMultimap.create(expectedIDsPerBatch, expectedPathsPerID);
		else
			idAndUrlMappedInput.clear();	// Clear it from its elements (without deallocating the memory), before gathering the next batch.

		int curBeginning = FileUtils.fileIndex;
		
		while ( inputScanner.hasNextLine() && (FileUtils.fileIndex < (curBeginning + jsonBatchSize)) )
		{// While (!EOF) and inside the current url-batch, iterate through lines.

			//logger.debug("fileIndex: " + FileUtils.fileIndex);	// DEBUG!

			// Take each line, remove potential double quotes.
			String retrievedLineStr = inputScanner.nextLine();
			//logger.debug("Loaded from inputFile: " + retrievedLineStr);	// DEBUG!

			FileUtils.fileIndex ++;

			if ( retrievedLineStr.isEmpty() ) {
				FileUtils.unretrievableInputLines ++;
				continue;
			}

			if ( (inputIdUrlTuple = getDecodedJson(retrievedLineStr)) == null ) {	// Decode the jsonLine and take the two attributes.
				logger.warn("A problematic inputLine found: \t" + retrievedLineStr);
				FileUtils.unretrievableInputLines ++;
				continue;
			}

			if ( !idAndUrlMappedInput.put(inputIdUrlTuple.id, inputIdUrlTuple.url) ) {    // We have a duplicate id-url pair in the input, log it here as we cannot pass it through the HashMultimap. We will handle the first found pair only.
				duplicateIdUrlEntries ++;
				UrlUtils.logOutputData(inputIdUrlTuple.id, inputIdUrlTuple.url, null, UrlUtils.duplicateUrlIndicator, "Discarded in FileUtils.getNextIdUrlPairBatchFromJson(), as it is a duplicate.", null, false, "false", "N/A", "N/A", "N/A", "true", null, "null");
			}
		}

		return idAndUrlMappedInput;
	}
	
	
	/**
	 * This method decodes a Jason String into its members.
	 * @param jsonLine String
	 * @return HashMap<String,String>
	 */
	public static IdUrlTuple getDecodedJson(String jsonLine)
	{
		// Get ID and url and put them in the HashMap
		String idStr = null;
		String urlStr = null;
		try {
			JSONObject jObj = new JSONObject(jsonLine); // Construct a JSONObject from the retrieved jsonLine.
			idStr = jObj.get("id").toString();
			urlStr = jObj.get("url").toString();
		} catch (JSONException je) {
			logger.warn("JSONException caught when tried to parse and extract values from jsonLine: \t" + jsonLine, je);
			return null;
		}

		if ( urlStr.isEmpty() ) {
			if ( !idStr.isEmpty() )	// If we only have the id, then go and log it.
				UrlUtils.logOutputData(idStr, urlStr, null, UrlUtils.unreachableDocOrDatasetUrlIndicator, "Discarded in FileUtils.jsonDecoder(), as the url was not found.", null, true, "true", "false", "false", "false", "false", null, "null");
			return null;
		}

		return new IdUrlTuple(idStr, urlStr);
	}
	
	
	/**
	 * This function writes new "quadruplesToBeLogged"(id-sourceUrl-docUrl-comment) in the output file.
	 * Each time it's finished writing, it flushes the write-stream and clears the "quadrupleToBeLoggedList".
	 */
	public static void writeResultsToFile()
	{
		if ( stringToBeWritten == null )
			stringToBeWritten = new StringBuilder(jsonBatchSize * 900);  // 900: the usual-maximum-expected-length for an <id-sourceUrl-docUrl-comment> quadruple.

		for ( DataToBeLogged data : FileUtils.dataToBeLoggedList )
		{
			stringToBeWritten.append(data.toJsonString()).append(endOfLine);
		}
		
		printStream.print(stringToBeWritten);
		printStream.flush();
		
		stringToBeWritten.setLength(0);	// Reset the buffer (the same space is still used, no reallocation is made).
		logger.debug("Finished writing " + FileUtils.dataToBeLoggedList.size() + " quadruples to the outputFile.");
		
		FileUtils.dataToBeLoggedList.clear();	// Clear the list to put the new <jsonBatchSize> values. The backing array used by List is not de-allocated. Only the String-references contained get GC-ed.
	}


	public static final AtomicInteger numOfDocFiles = new AtomicInteger(0);

	public static DocFileData storeDocFileWithIdOrOriginalFileName(HttpURLConnection conn, String docUrl, String id, int contentSize) throws DocFileNotRetrievedException
	{
		DocFileData docFileData;
		if ( docFileNameType.equals(DocFileNameType.idName) )
			docFileData = getDocFileAndHandleExisting(id, ".pdf", false);    // TODO - Later, on different fileTypes, take care of the extension properly.
		else if ( docFileNameType.equals(DocFileNameType.originalName) )
			docFileData = getDocFileWithOriginalFileName(docUrl, conn.getHeaderField("Content-Disposition"));
		else
			throw new DocFileNotRetrievedException("The 'docFileNameType' was invalid: " + docFileNameType);

		numOfDocFiles.incrementAndGet();

		File docFile = docFileData.getDocFile();

		InputStream inputStream = ConnSupportUtils.checkEncodingAndGetInputStream(conn, false);
		if ( inputStream == null )
			throw new DocFileNotRetrievedException("Could not acquire the inputStream!");

		MessageDigest md;
		try {
			md = MessageDigest.getInstance("MD5");
		} catch (Exception e) {
			logger.error("Failed to get instance for MD5 hash-algorithm!", e);
			throw new RuntimeException("MD5 HASH ALGO MISSING");
		}
		long bytesCount = 0;
		FileOutputStream fileOutputStream = docFileData.getFileOutputStream();
		int bufferSize = (((contentSize != -2) && contentSize < fiveMb) ? contentSize : fiveMb);

		try ( BufferedInputStream inStream = new BufferedInputStream(inputStream, bufferSize);
			  BufferedOutputStream outStream = new BufferedOutputStream(((fileOutputStream != null) ? fileOutputStream : new FileOutputStream(docFile)), bufferSize) )
		{
			int maxStoringWaitingTime = getMaxStoringWaitingTime(contentSize);	// It handles the "-2" case.
			int readByte = -1;
			long startTime = System.nanoTime();
			while ( (readByte = inStream.read()) != -1 )
			{
				long elapsedTime = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startTime);
				if ( (elapsedTime > maxStoringWaitingTime) || (elapsedTime == Long.MIN_VALUE) ) {
					String errMsg = "Storing docFile from docUrl: \"" + docUrl + "\" is taking over " + TimeUnit.MILLISECONDS.toSeconds(maxStoringWaitingTime) + " seconds! Aborting..";
					logger.warn(errMsg);
					try {
						FileDeleteStrategy.FORCE.delete(docFile);
					} catch (Exception e) {
						logger.error("Error when deleting the half-retrieved file from docUrl: " + docUrl);
					}
					numOfDocFiles.decrementAndGet();	// Revert number, as this docFile was not retrieved.
					throw new DocFileNotRetrievedException(errMsg);
				} else {
					outStream.write(readByte);
					md.update((byte) readByte);
					bytesCount++;
				}
			}
			//logger.debug("Elapsed time for storing: " + TimeUnit.NANOSECONDS.toSeconds(System.nanoTime() - startTime));

			String md5Hash = DatatypeConverter.printHexBinary(md.digest()).toLowerCase();

			if ( shouldUploadFilesToS3 ) {
				docFileData = S3ObjectStore.uploadToS3(docFile.getName(), docFile.getAbsolutePath());
				if ( docFileData != null ) {    // Otherwise, the returned object will be null.
					docFileData.setDocFile(docFile);
					docFileData.setHash(md5Hash);
					docFileData.setSize(bytesCount);
					// In the S3 case, we use IDs or increment-numbers as the names, so no duplicate-overwrite should be a problem here.
					// as we delete the local files and the online tool just overwrites the file, without responding if it was overwritten.
					// So if the other naming methods were used with S3, we would have to check if the file existed online and then rename of needed and upload back.
				} else
					numOfDocFiles.decrementAndGet();	// Revert number, as this docFile was not retrieved. In case of delete-failure, this file will just be overwritten, except if it's the last one.
			} else
				docFileData = new DocFileData(docFile, md5Hash, bytesCount, ((FileUtils.shouldLogFullPathName) ? docFile.getAbsolutePath() : docFile.getName()));

			// TODO - HOW TO SPOT DUPLICATE-NAMES IN THE S3 MODE?
			// The local files are deleted after uploaded.. (as they should be)
			// So we will be uploading files with the same filename-KEY.. in that case, they get overwritten.
			// An option would be to check if an object already exists, then increment a number and upload the object.
			// From that moment forward, the number will be stored in memory along with the fileKeyName, just like with "originalNames", so next time no online check should be needed..!
			// Of-course the above fast-check algorithm would work only if the bucket was created or filled for the first time, from this program, in a single machine.
			// Otherwise, a file-key-name (with incremented number-string) might already exist, from a previous or parallel upload from another run and so it will be overwritten!

			return docFileData;	// It may be null.

		} catch (DocFileNotRetrievedException dfnre) {
			throw dfnre;	// No reversion of the number needed.
		} catch (FileNotFoundException fnfe) {	// This may be thrown in case the file cannot be created.
			logger.error("", fnfe);
			numOfDocFiles.decrementAndGet();
			// When creating the above FileOutputStream, the file may be created as an "empty file", like a zero-byte file, when there is a "No space left on device" error.
			// So the empty file may exist, but we will also get the "FileNotFoundException".
			try {
				if ( docFile.exists() )
					FileDeleteStrategy.FORCE.delete(docFile);
			} catch (Exception e) {
				logger.error("Error when deleting the half-created file from docUrl: " + docUrl);
			}
			throw new DocFileNotRetrievedException(fnfe.getMessage());
		} catch (IOException ioe) {
			numOfDocFiles.decrementAndGet();	// Revert number, as this docFile was not retrieved.
			throw new DocFileNotRetrievedException(ioe.getMessage());
		} catch (Exception e) {
			numOfDocFiles.decrementAndGet();	// Revert number, as this docFile was not retrieved.
			logger.error("", e);
			throw new DocFileNotRetrievedException(e.getMessage());
		}
	}


	/**
	 * This method is responsible for storing the docFiles and store them in permanent storage.
	 * It is synchronized, in order to avoid files' numbering inconsistency.
	 *
	 * @param conn
	 * @param docUrl
	 * @param contentSize
	 * @throws DocFileNotRetrievedException
	 */
	public static synchronized DocFileData storeDocFileWithNumberName(HttpURLConnection conn, String docUrl, int contentSize) throws DocFileNotRetrievedException
	{
		File docFile = new File(storeDocFilesDir + (numOfDocFile++) + ".pdf");	// First use the "numOfDocFile" and then increment it.
		// TODO - Later, on different fileTypes, take care of the extension properly.

		InputStream inputStream = ConnSupportUtils.checkEncodingAndGetInputStream(conn, false);
		if ( inputStream == null )
			throw new DocFileNotRetrievedException("Could not acquire the inputStream!");

		MessageDigest md;
		try {
			md = MessageDigest.getInstance("MD5");
		} catch (Exception e) {
			logger.error("Failed to get instance for MD5 hash-algorithm!", e);
			throw new RuntimeException("MD5 HASH ALGO MISSING");
		}
		long bytesCount = 0;
		int bufferSize = (((contentSize != -2) && contentSize < fiveMb) ? contentSize : fiveMb);

		try ( BufferedInputStream inStream = new BufferedInputStream(inputStream, bufferSize);
			BufferedOutputStream outStream = new BufferedOutputStream(new FileOutputStream(docFile), bufferSize))
		{
			int maxStoringWaitingTime = getMaxStoringWaitingTime(contentSize);	// It handles the "-2" case.
			int readByte = -1;
			long startTime = System.nanoTime();
			while ( (readByte = inStream.read()) != -1 )
			{
				long elapsedTime = TimeUnit.NANOSECONDS.toMillis(System.nanoTime() - startTime);
				if ( (elapsedTime > maxStoringWaitingTime) || (elapsedTime == Long.MIN_VALUE) ) {
					String errMsg = "Storing docFile from docUrl: \"" + docUrl + "\" is taking over " + TimeUnit.MILLISECONDS.toSeconds(maxStoringWaitingTime) + " seconds! Aborting..";
					logger.warn(errMsg);
					try {
						FileDeleteStrategy.FORCE.delete(docFile);
					} catch (Exception e) {
						logger.error("Error when deleting the half-retrieved file from docUrl: " + docUrl);
					}
					numOfDocFile --;	// Revert number, as this docFile was not retrieved. In case of delete-failure, this file will just be overwritten, except if it's the last one.
					throw new DocFileNotRetrievedException(errMsg);
				} else {
					outStream.write(readByte);
					md.update((byte) readByte);
					bytesCount++;
				}
			}
			//logger.debug("Elapsed time for storing: " + TimeUnit.NANOSECONDS.toSeconds(System.nanoTime() - startTime));

			String md5Hash = DatatypeConverter.printHexBinary(md.digest()).toLowerCase();

			DocFileData docFileData;
			if ( shouldUploadFilesToS3 ) {
				docFileData = S3ObjectStore.uploadToS3(docFile.getName(), docFile.getAbsolutePath());
				if ( docFileData != null ) {    // Otherwise, the returned object will be null.
					docFileData.setDocFile(docFile);
					docFileData.setHash(md5Hash);
					docFileData.setSize(bytesCount);
					// In the S3 case, we use IDs or increment-numbers as the names, so no duplicate-overwrite should be a problem here.
					// as we delete the local files and the online tool just overwrites the file, without responding if it was overwritten.
					// So if the other naming methods were used with S3, we would have to check if the file existed online and then rename of needed and upload back.
				} else
					numOfDocFile --;
			} else
				docFileData = new DocFileData(docFile, md5Hash, bytesCount, ((FileUtils.shouldLogFullPathName) ? docFile.getAbsolutePath() : docFile.getName()));

			// TODO - HOW TO SPOT DUPLICATE-NAMES IN THE S3 MODE?
			// The local files are deleted after uploaded.. (as they should be)
			// So we will be uploading files with the same filename-KEY.. in that case, they get overwritten.
			// An option would be to check if an object already exists, then increment a number and upload the object.
			// From that moment forward, the number will be stored in memory along with the fileKeyName, just like with "originalNames", so next time no online check should be needed..!
			// Of-course the above fast-check algorithm would work only if the bucket was created or filled for the first time, from this program, in a single machine.
			// Otherwise, a file-key-name (with incremented number-string) might already exist, from a previous or parallel upload from another run and so it will be overwritten!

			return docFileData;	// It may be null.
			
		} catch (DocFileNotRetrievedException dfnre) {
			throw dfnre;	// No reversion of the number needed.
		} catch (FileNotFoundException fnfe) {	// This may be thrown in the file cannot be created.
			logger.error("", fnfe);
			numOfDocFile --;	// Revert number, as this docFile was not retrieved. In case of delete-failure, this file will just be overwritten, except if it's the last one.
			// When creating the above FileOutputStream, the file may be created as an "empty file", like a zero-byte file, when there is a "No space left on device" error.
			// So the empty file may exist, but we will also get the "FileNotFoundException".
			try {
				if ( docFile.exists() )
					FileDeleteStrategy.FORCE.delete(docFile);
			} catch (Exception e) {
				logger.error("Error when deleting the half-created file from docUrl: " + docUrl);
			}
			throw new DocFileNotRetrievedException(fnfe.getMessage());
		} catch (IOException ioe) {
			numOfDocFile --;	// Revert number, as this docFile was not retrieved. In case of delete-failure, this file will just be overwritten, except if it's the last one.
			throw new DocFileNotRetrievedException(ioe.getMessage());
		} catch (Exception e) {
			numOfDocFile --;	// Revert number, as this docFile was not retrieved. In case of delete-failure, this file will just be overwritten, except if it's the last one.
			logger.error("", e);
			throw new DocFileNotRetrievedException(e.getMessage());
		}
	}


	/**
	 * This method Returns the Document-"File" object which has the original file name as the final fileName.
	 * It is effectively synchronized, since it's always called from a synchronized method.
	 * @param docUrl
	 * @param contentDisposition
	 * @return
	 * @throws DocFileNotRetrievedException
	 */
	public static DocFileData getDocFileWithOriginalFileName(String docUrl, String contentDisposition) throws  DocFileNotRetrievedException
	{
		String docFileName = null;
		boolean hasUnretrievableDocName = false;
		
		String dotFileExtension /*= "";
		if ( shouldAcceptOnlyPDFs )
			dotFileExtension*/ = ".pdf";
		/*else {	// TODO - Later we might accept more fileTypes.
			if ( contentType != null )
				// Use the Content-Type to determine the extension. A multi-mapping between mimeTypes and fileExtensions is needed.
			else
				// Use the last subString of the url-string as last resort, although not reliable! (subString after the last "." will not work if the docFileName-url-part doesn't include is not an extension but part of the original name or a "random"-string).
		}*/
		
		if ( contentDisposition != null ) {	// Extract docFileName from contentDisposition.
			Matcher fileNameMatcher = FILENAME_FROM_CONTENT_DISPOSITION_FILTER.matcher(contentDisposition);
			if ( fileNameMatcher.matches() ) {
				try {
					docFileName = fileNameMatcher.group(1);	// Group<1> is the fileName.
				} catch (Exception e) { logger.error("", e); }
				if ( (docFileName == null) || docFileName.isEmpty() )
					docFileName = null;	// Ensure null-value for future checks.
			} else
				logger.warn("Unmatched file-content-Disposition: " + contentDisposition);
		}
		
		//docFileName = null;	// Just to test the docFileNames retrieved from the DocId-part of the docUrls.
		
		// If we couldn't get the fileName from the "Content-Disposition", try getting it from the url.
		if ( docFileName == null )
			docFileName = UrlUtils.getDocIdStr(docUrl, null);	// Extract the docID as the fileName from docUrl.
		
		if ( (docFileName != null) && !docFileName.isEmpty() )	// Re-check as the value might have changed.
		{
			if ( !docFileName.endsWith(dotFileExtension) )
				docFileName += dotFileExtension;
			
			String fullDocName = storeDocFilesDir + docFileName;

			// Check if the FileName is too long, and we are going to get an error at file-creation.
			int docFullNameLength = fullDocName.length();
			if ( docFullNameLength > MAX_FILENAME_LENGTH ) {
				logger.warn("Too long docFullName found (" + docFullNameLength + " chars), it would cause file-creation to fail, so we mark the file-name as \"unretrievable\".\nThe long docName is: \"" + fullDocName + "\".");
				hasUnretrievableDocName = true;	// TODO - Maybe I should take the part of the full name that can be accepted instead of marking it unretrievable..
			}
		} else
			hasUnretrievableDocName = true;

		if ( hasUnretrievableDocName ) {
			// If this ever is called from a code block without synchronization, then it should be a synchronized block.
			if ( unretrievableDocNamesNum == 0 )
				docFileName = "unretrievableDocName" + dotFileExtension;
			else
				docFileName = "unretrievableDocName(" + unretrievableDocNamesNum + ")" + dotFileExtension;

			unretrievableDocNamesNum ++;
		}
		
		//logger.debug("docFileName: " + docFileName);

		return getDocFileAndHandleExisting(docFileName, dotFileExtension, hasUnretrievableDocName);
	}


	private static final Lock fileNameLock = new ReentrantLock(true);

	public static DocFileData getDocFileAndHandleExisting(String docFileName, String dotFileExtension, boolean hasUnretrievableDocName) throws  DocFileNotRetrievedException
	{
		String saveDocFileFullPath = storeDocFilesDir + docFileName;
		if ( ! docFileName.endsWith(dotFileExtension) )
			saveDocFileFullPath += dotFileExtension;

		File docFile = new File(saveDocFileFullPath);
		FileOutputStream fileOutputStream = null;
		Integer curDuplicateNum = 0;

		// Synchronize to avoid file-overriding and corruption when multiple thread try to store a file with the same name (like when there are multiple files related with the same ID), which results also in loosing docFiles.
		// The file is created inside the synchronized block, by initializing the "fileOutputStream", so the next thread to check if it is going to download a duplicate-named file is guaranteed to find the previous file in the file-system
		// (without putting the file-creation inside the locks, the previous thread might have not created the file in time and the next thread will just override it, instead of creating a new file)
		fileNameLock.lock();
		try {
			if ( !hasUnretrievableDocName )	// If we retrieved the fileName, go check if it's a duplicate.
			{
				if ( (curDuplicateNum = numbersOfDuplicateDocFileNames.get(docFileName)) != null )	// Since this data-structure is accessed inside the SYNCHRONIZED BLOCK, it can simpy be a HashMap without any internal sync, in order to speed it up.
					curDuplicateNum += 1;
				else if ( docFile.exists() )	// If it's not an already-known duplicate (this is the first duplicate-case for this file), go check if it exists in the fileSystem.
					curDuplicateNum = 1;	// It was "null", after the "ConcurrentHashMap.get()" check.
				else
					curDuplicateNum = 0;

				if ( curDuplicateNum > 0 ) {	// Construct final-DocFileName for this docFile.
					String preExtensionFileName = docFileName;
					int lastIndexOfDot = docFileName.lastIndexOf(".");
					if ( lastIndexOfDot != -1 )
						preExtensionFileName = docFileName.substring(0, lastIndexOfDot);
					docFileName = preExtensionFileName + "(" + curDuplicateNum + ")" + dotFileExtension;
					saveDocFileFullPath = storeDocFilesDir + docFileName;
					docFile = new File(saveDocFileFullPath);
				}
			}

			fileOutputStream = new FileOutputStream(docFile);
			if ( curDuplicateNum > 0 )	// After the file is created successfully, from the above outputStream-initialization, add the new duplicate-num in our HashMap.
				numbersOfDuplicateDocFileNames.put(docFileName, curDuplicateNum);    // We should add the new "curDuplicateNum" for the original fileName, only if the new file can be created.

		} catch (FileNotFoundException fnfe) {	// This may be thrown in case the file cannot be created.
			logger.error("", fnfe);
			// When creating the above FileOutputStream, the file may be created as an "empty file", like a zero-byte file, when there is a "No space left on device" error.
			// So the empty file may exist, but we will also get the "FileNotFoundException".
			try {
				if ( docFile.exists() )
					FileDeleteStrategy.FORCE.delete(docFile);
			} catch (Exception e) {
				logger.error("Error when deleting the half-created file: " + docFileName);
			}
			// The "fileOutputStream" was not created in this case, so no closing is needed.
			throw new DocFileNotRetrievedException(fnfe.getMessage());
		} catch (Exception e) {	// Mostly I/O and Security Exceptions.
			if ( fileOutputStream != null ) {
				try {
					fileOutputStream.close();
				} catch (Exception ignored) {}
			}
			String errMsg = "Error when handling the fileName = \"" + docFileName + "\" and dotFileExtension = \"" + dotFileExtension + "\"!";
			logger.error(errMsg, e);
			throw new DocFileNotRetrievedException(errMsg);
		} finally {
			fileNameLock.unlock();
		}

		return new DocFileData(docFile, fileOutputStream);
	}


	static final int mb = 1_048_576;

	public static final int fiveMb = (5 * mb);

	static final int fiftyMBInBytes = (50 * mb);
	static final int oneHundredMBInBytes = (100 * mb);
	static final int twoHundredMBInBytes = (200 * mb);
	static final int threeHundredMBInBytes = (300 * mb);


	private static int getMaxStoringWaitingTime(int contentSize)
	{
		if ( contentSize != -2 ) {
			if ( contentSize <= fiftyMBInBytes )
				return 45_000;	// 45 seconds
			else if ( contentSize <= oneHundredMBInBytes )
				return 60_000;	// 1 min.
			else if ( contentSize <= twoHundredMBInBytes )
				return 120_000;	// 2 mins.
			else if ( contentSize <= threeHundredMBInBytes )
				return 180_000;	// 3 mins.
			else
				return 300_000;	// 5 mins.
		}
		else	// In case the server did not provide the "Content Length" header.
			return 45_000;	// 45 seconds
	}

	
	/**
	 * Closes open Streams and deletes the temporary-inputFile which is used when the MLA is enabled.
	 */
	public static void closeIO()
	{
		if ( inputScanner != null )
        	inputScanner.close();
		
		if ( printStream != null )
			printStream.close();

		// If the MLA was enabled then an extra file was used to store the streamed content and count the number of urls, in order to optimize the M.L.A.'s execution.
		if ( fullInputFilePath != null ) {
			try {
				org.apache.commons.io.FileUtils.forceDelete(new File(fullInputFilePath));
			} catch (Exception e) {
				logger.error("", e);
				closeLogger();
				PublicationsRetriever.executor.shutdownNow();
				System.exit(-11);
			}
		}
		closeLogger();
	}
	
	
	private static void closeLogger()
	{
		LoggerContext loggerContext = (LoggerContext) LoggerFactory.getILoggerFactory();
		loggerContext.stop();
	}
	
	
	/**
	 * This method parses a testFile with one-url-per-line and extracts the urls (e.g. ".txt", ".csv", ".tsv").
	 * @return Collection<String>
	 */
	public static Collection<String> getNextUrlBatchTest()
	{
		Collection<String> urlGroup = new HashSet<String>(jsonBatchSize);
		
		// Take a batch of <jsonBatchSize> urls from the file..
		// If we are at the end and there are less than <jsonBatchSize>.. take as many as there are..
		
		//logger.debug("Retrieving the next batch of " + jsonBatchSize + " elements from the inputFile.");
		int curBeginning = FileUtils.fileIndex;
		
		while ( inputScanner.hasNextLine() && (FileUtils.fileIndex < (curBeginning + jsonBatchSize)) )
		{// While (!EOF) and inside the current url-batch, iterate through lines.
			
			// Take each line, remove potential double quotes.
			String retrievedLineStr = inputScanner.nextLine();
			
			FileUtils.fileIndex ++;
			
			if ( (FileUtils.fileIndex == 1) && skipFirstRow )
				continue;
			
			if ( retrievedLineStr.isEmpty() ) {
				FileUtils.unretrievableInputLines ++;
				continue;
			}
			
			retrievedLineStr = StringUtils.remove(retrievedLineStr, "\"");
			
			//logger.debug("Loaded from inputFile: " + retrievedLineStr);	// DEBUG!

			if ( !urlGroup.add(retrievedLineStr) )    // We have a duplicate in the input.. log it here as we cannot pass it through the HashSet. It's possible that this as well as the original might be/give a docUrl.
				UrlUtils.logOutputData(null, retrievedLineStr, null, UrlUtils.duplicateUrlIndicator, "Discarded in FileUtils.getNextUrlGroupTest(), as it is a duplicate.", null, false, "false", "N/A", "N/A", "N/A", "true", null, "null");
		}

		return urlGroup;
	}

}
