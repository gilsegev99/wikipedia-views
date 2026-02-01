import sys
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from pyspark.sql.functions import explode, concat_ws, col
from awsglue.context import GlueContext
from awsglue.job import Job

args = getResolvedOptions(sys.argv, ["JOB_NAME"])
sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session
job = Job(glueContext)
job.init(args["JOB_NAME"], args)

# Extract raw json data and organise dataframe

df_raw = spark.read.json("s3a://wikimedia-data-bucket/raw/views_data/*.json") # Convert to DataFrame if needed

df_items = df_raw.select(explode(col("items")).alias("items"))

df_structured = df_items.select(concat_ws("-", col("items.year"), col("items.month"), col("items.day")).alias("date"),
                                explode(col("items.articles")).alias("article_data")
)

df_final = df_structured.select(col("date"),
                                col("article_data.article").alias("article"),
                                col("article_data.views").alias("views"),
                                col("article_data.rank").alias("rank")
                                
)

# Write output to parquet. We use 'overwrite' for idempotency and snappy compression for read/write speed.

output_location = "s3a://wikimedia-data-bucket/processed/views_data/"
df_final.write \
    .mode("overwrite") \
    .option("compression", "snappy") \
    .parquet(output_location)

print(f"Number of rows: {df_final.count()}")

# df_final.printSchema()
df_final.show(20, truncate=False)

job.commit()