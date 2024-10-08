mongo_ip = process.env.MONGO_IP
mongo_user = process.env.MONGO_USER
mongo_pass = process.env.MONGO_PASS
mongo_db = process.env.MONGO_DB
dblp_dataset = `${process.env.DBLP_DATASET}_${process.env.LATEST_DATE}`

db = connect(`mongodb://${mongo_user}:${mongo_pass}@${mongo_ip}:27017/${mongo_db}?authSource=admin`);

query = db[dblp_dataset].aggregate([
  {
    $project: {
      count: {
        $size: {
          $filter: {
            input: "$cited_papers",
            as: "paper",
            cond: {
              $or: [
                { $ifNull: ["$$paper.dblp_id", false] },
                { $ifNull: ["$$paper.doi", false] }
              ]
            }
          }
        }
      }
    }
  },
  {
    $group: {
      _id: null,
      total_count: {
        $sum: "$count"
      }
    }
  }
]);

// Extract the total_count value from the aggregation result
result = query.toArray(); // Convert the result to an array
if (result.length > 0) {
  print(`\n-----------------------------\nTotal citation count: ${result[0].total_count}\n-----------------------------\n`);
} else {
  print("No data found");
}
