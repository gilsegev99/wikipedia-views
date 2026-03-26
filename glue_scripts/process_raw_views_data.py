import sys
import boto3
from awsglue.transforms import *
from awsglue.utils import getResolvedOptions
from awsglue.dynamicframe import DynamicFrame
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

print(f"Number of rows: {df_final.count()}")
df_final.printSchema()

# Write output to parquet. We overwrite for idempotency and use snappy compression for read/write speed.
output_location = "s3://wikimedia-data-bucket/processed/views_data/"
glue_dynamic_frame_final = DynamicFrame.fromDF(df_final, glueContext)

s3 = boto3.resource('s3')
bucket = s3.Bucket('wikimedia-data-bucket')
bucket.objects.filter(Prefix='processed/views_data/').delete()

s3output = glueContext.getSink(
  path=output_location,
  connection_type="s3",
  updateBehavior="UPDATE_IN_DATABASE",
  partitionKeys=[],
  compression="snappy",
  enableUpdateCatalog=True,
  transformation_ctx="s3output",
)

s3output.setCatalogInfo(
  catalogDatabase="wikimedia-data", catalogTableName="processed_views_data"
)

s3output.setFormat("glueparquet")
s3output.writeFrame(glue_dynamic_frame_final)

job.commit()