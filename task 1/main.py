from api import *

import asyncio


async def main():
    user_input = input("Enter a customer support ticket:\n")

    #log user input
    print("\nProcessing ticket...\n")
    print("User input:", user_input)

    #Main pipeline 
    #A chained approach where the output of one step feeds into the next

    
    #1.Get input cleaned and normalized

    #2.Classify input
        #Parallelize sentiment analysis and keyword extraction to speed up processing
            #a. Sentiment analysis
            #b. Keyword extraction
        #Combine and make an overall classification of the ticket based on sentiment and keywords


    #3.Generate response


    # Step 1: Clean the input
    print("\nCleaning input...")
    cleaned_input = clean_user_input(user_input)
    print("\nCleaned Input:", cleaned_input)

    # Step 2: Parallelize sentiment analysis and keyword extraction
    print("\nGenerating sentiment and keywords...")
    sentiment_and_keywords = await generate_sentiment_and_keywords(cleaned_input)
    print("\nSentiment and Keywords:", sentiment_and_keywords)
    # Use cleaned_input and sentiment_and_keywords to Classify the input
    print("\nClassifying input...")
    classified_data = classify_input(cleaned_input, sentiment_and_keywords)
    print("\nClassified Data:", classified_data)

    # Step 3: Generate the response
    print("\nGenerating response...")
    response = route_issue(classified_data)
    print("\nResponse:", response)




if __name__ == "__main__":
    asyncio.run(main())