import pandas as pd
import io
import logging
logger = logging.getLogger()

def default_bucket(session):
    '''
    Return the s3 bucket name for athena results
    to allow us to get the csv natively
    '''
    account_id = session.client('sts').get_caller_identity().get('Account')
    return '{}-{}-query-results-{}'.format(account_id, 'aws-athena',  session.region_name)    

def run_query(athena, query, database, s3_output):
    ''' 
    Function for executing Athena queries and return the query ID 
    '''
    response = athena.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': database
            },
        ResultConfiguration={
            'OutputLocation': 's3://{}'.format(s3_output),
            }
        )
    logger.debug('Execution ID: ' + response['QueryExecutionId'])
    return response

def dataframe_from_athena_s3(session,athena_response,bucket_name):
    '''
    Retrieve the native athena csv results as a pandas dataframe
    for easy conversion and analysis
    '''
    s3=session.resource('s3')
    key_name=athena_response['QueryExecutionId']
    s3_response = s3.Bucket(bucket_name).Object(key= key_name + '.csv').get()

    return pd.read_csv(io.BytesIO(s3_response['Body'].read()), encoding='utf8') 