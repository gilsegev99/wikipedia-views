# Wikimedia Data Extraction Pipeline (wip)

## Project Background

This project aims to unlock insights into which topics - including news stories, famous figures, events and art - were trending during any time period in the last 10 years. These insights give an impression of what English speaking internet users were interested in reading about on a day-to-day basis.

The [Wikimedia Analytics API](https://doc.wikimedia.org/generated-data-platform/aqs/analytics-api/concepts/page-views.html) makes this project possible, which provides readily available data on the most-viewed Wikipedia articles on any particular day. The [MediaWiki API](https://en.wikipedia.org/w/api.php) enriches this data further with common categories that each article belongs to, making trends over time more apparent.

This project implements an automated data extraction pipeline that retrieves data from the Wikimedia API and stores it in AWS S3. The pipeline runs daily to collect current data and includes a backfill mechanism to retrieve historical data for any specified date range.

The solution leverages AWS serverless technologies to create a scalable, cost-effective, and maintainable data pipeline. By using Lambda functions for compute, S3 for storage, EventBridge for scheduling, and Step Functions for orchestration, the infrastructure requires minimal operational overhead while providing reliable data collection capabilities.

### Use Cases

- Daily automated data collection from Wikimedia APIs
- Historical data backfills for analytics and reporting
- Building datasets for machine learning or research purposes
- Monitoring Wikimedia content trends over time

## Stack Details

### AWS Services

- **AWS Lambda**: Serverless compute for executing data extraction logic
  - Main Lambda: Calls Wikimedia API and writes data to S3
  - Date Range Generator Lambda: Generates date arrays for backfill operations
- **Amazon S3**: Object storage for extracted Wikimedia data
- **Amazon EventBridge**: Scheduled event triggers for daily pipeline execution
- **AWS Step Functions**: Orchestration of backfill state machine workflows
- **AWS IAM**: Identity and access management for service permissions

### Technologies

- **Python 3.x**: Primary programming language for Lambda functions
- **Terraform**: Infrastructure as Code (IaC) for AWS resource provisioning
- **AWS CLI**: Command-line interface for AWS service management

## Architecture

### Architecture Diagram

![Architecture Diagram](docs/architecture-diagram.png)

### Daily Pipeline Flow

1. **EventBridge Rule** triggers the main Lambda function on a daily schedule (configurable via cron expression)
2. **Main Lambda Function** executes:
   - Calls the Wikimedia API to extract data
   - Processes and formats the response
   - Writes the data to S3 with date-based partitioning
3. **S3 Bucket** stores the extracted data in a structured format

### Backfill Process Flow

1. **Manual Trigger** starts the Step Functions state machine with start/end date parameters
2. **Date Range Generator Lambda** executes:
   - Receives start and end date from state machine input
   - Generates an array of all dates in the specified range
   - Returns the date array to Step Functions
3. **Map State** in Step Functions:
   - Iterates over each date in the array
   - Executes iterations in parallel (configurable concurrency)
4. **Main Lambda Function** executes for each date:
   - Fetches data from Wikimedia API for the specific date
   - Writes data to S3 with appropriate date partitioning

### Data Storage Pattern

Data is stored in S3 with the following structure:
```
s3://wiki-media-data-bucket/
  └── raw/
      ├── category_data/
      │   └── article.json
      │           └── data.json
      └── views_data/
          └── YYYY-MM-DD.json              
```

## Getting Started

### Setup

Follow the detailed instructions in [SETUP.md](SETUP.md).


## Monitoring and Logging

- **CloudWatch Logs**: All Lambda function logs are automatically sent to CloudWatch
- **CloudWatch Metrics**: Lambda invocations, errors, and duration metrics
- **Step Functions Console**: Visual monitoring of backfill executions
- **S3 Event Notifications**: (Optional) Configure notifications for new data uploads

## Cost Considerations

This serverless architecture is designed to be cost-effective:

- Lambda charges based on actual execution time
- S3 charges based on storage used
- EventBridge rules have minimal cost
- Step Functions charges per state transition

Estimated monthly cost for typical usage: $5-20 USD (depends on data volume and frequency)

## Future Improvements

### High Priority

- [ ] Add error handling and retry logic for API failures
- [ ] Implement data validation before S3 upload
- [ ] Add CloudWatch alarms for pipeline failures
- [ ] Create SNS notifications for backfill completion/failures
- [ ] Add unit tests for Lambda functions
- [ ] Implement integration tests for the full pipeline

### Medium Priority

- [ ] Add data transformation layer using AWS Glue
- [ ] Create AWS Glue Data Catalog for extracted data
- [ ] Implement incremental data loading instead of full extracts
- [ ] Add support for multiple Wikimedia API endpoints
- [ ] Create CloudFormation templates as alternative to Terraform
- [ ] Add data quality checks and metrics
- [ ] Implement data lifecycle policies for S3 (archival/deletion)

### Low Priority

- [ ] Build a simple dashboard for monitoring extraction metrics
- [ ] Add support for different output formats (Parquet, CSV)
- [ ] Implement API rate limiting and throttling controls
- [ ] Add support for real-time streaming using Kinesis
- [ ] Implement cost optimization with Reserved Concurrency
- [ ] Add multi-region deployment support

### Technical Debt

- [ ] Refactor Lambda functions for better modularity
- [ ] Add comprehensive logging and observability
- [ ] Implement proper secret management using AWS Secrets Manager
- [ ] Add CI/CD pipeline for automated deployments
- [ ] Create detailed API documentation
- [ ] Implement infrastructure testing with Terratest



## Acknowledgments

- Wikimedia Foundation for providing the API
- AWS for serverless infrastructure services
- Terraform community for IaC best practices

## Contact

For questions or issues, please open an issue in this repository.

---

**Note**: Replace placeholder values (like state machine ARN, email addresses, and architecture diagram path) with your actual project details.