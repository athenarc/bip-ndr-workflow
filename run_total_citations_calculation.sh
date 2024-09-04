export $(xargs < .env)

mongosh --file calculate_total_citations_mongo.js