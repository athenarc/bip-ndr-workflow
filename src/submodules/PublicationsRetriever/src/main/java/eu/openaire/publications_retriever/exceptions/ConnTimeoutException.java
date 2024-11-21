package eu.openaire.publications_retriever.exceptions;


/**
 * This class implements the new custom exception: "ConnTimeoutException".
 * This exception is thrown when there is any kind of "connection-TimeoutException".
 * The calling method can decide what action to take, for example: stop crawling of the page immediately.
 * @author Lampros Smyrnaios
 */
public class ConnTimeoutException extends Exception{
	
	public ConnTimeoutException() {}
}
