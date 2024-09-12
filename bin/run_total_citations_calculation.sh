export $(xargs < .env)

mongosh --file dbscripts/calculate_total_citations_mongo.js