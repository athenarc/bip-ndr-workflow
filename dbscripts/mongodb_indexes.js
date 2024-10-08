use DBLP

db.manuscript_metadata.createIndex({"import_date": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"ee": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"ee-type": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"filename": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"filename_norm": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"key": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"key_norm": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"PDF_downloaded": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"title": 1}, {collation: {'locale': 'en', 'strength': 2}})
db.manuscript_metadata.createIndex({"title_concat": 1}, {collation: {'locale': 'en', 'strength': 2}})