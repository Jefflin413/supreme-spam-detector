# A basic spam classifier for  messages using Apache MXNet as deep learning framework.
# The idea is to use the SMS spam collection dataset available at <a href="https://archive.ics.uci.edu/ml/datasets/sms+spam+collection">https://archive.ics.uci.edu/ml/datasets/sms+spam+collection</a> to train and deploy a neural network model by leveraging on the built-in open-source container for Apache MXNet available in Amazon SageMaker.

from sagemaker import get_execution_role
import os
import pandas as pd
import numpy as np
import pickle
from utilities import one_hot_encode
from utilities import vectorize_sequences
import boto3
from sagemaker.mxnet import MXNet

bucket_name = "spam-filter-hw4"

role = get_execution_role()
bucket_key_prefix = "sms-spam-classifier"
vocabulary_length = 9013  # hardcoded


# Download the dataset
os.system("mkdir -p dataset")
os.system(
    "curl https://archive.ics.uci.edu/ml/machine-learning-databases/00228/smsspamcollection.zip -o dataset/smsspamcollection.zip"
)
os.system("unzip -o dataset/smsspamcollection.zip -d dataset")
os.system("head -10 dataset/SMSSpamCollection")


# We now load the dataset into a Pandas dataframe and execute some data preparation.
# More specifically we have to:
# replace the target column values (ham/spam) with numeric values (0/1)
# tokenize the sms messages and encode based on word counts
# split into train and test sets
# upload to a S3 bucket for training


df = pd.read_csv("dataset/SMSSpamCollection", sep="\t", header=None)
df[df.columns[0]] = df[df.columns[0]].map({"ham": 0, "spam": 1})

targets = df[df.columns[0]].values
messages = df[df.columns[1]].values

# one hot encoding for each SMS message
one_hot_data = one_hot_encode(messages, vocabulary_length)
encoded_messages = vectorize_sequences(one_hot_data, vocabulary_length)

df2 = pd.DataFrame(encoded_messages)
df2.insert(0, "spam", targets)

# Split into training and validation sets (80%/20% split)
split_index = int(np.ceil(df.shape[0] * 0.8))
train_set = df2[:split_index]
val_set = df2[split_index:]

train_set.to_csv(
    "dataset/sms_train_set.gz", header=False, index=False, compression="gzip"
)
val_set.to_csv("dataset/sms_val_set.gz", header=False, index=False, compression="gzip")


# We have to upload the two files back to Amazon S3 in order to be accessed by the Amazon SageMaker training cluster.


s3 = boto3.resource("s3")
target_bucket = s3.Bucket(bucket_name)

with open("dataset/sms_train_set.gz", "rb") as data:
    target_bucket.upload_fileobj(
        data, "{0}/train/sms_train_set.gz".format(bucket_key_prefix)
    )

with open("dataset/sms_val_set.gz", "rb") as data:
    target_bucket.upload_fileobj(
        data, "{0}/val/sms_val_set.gz".format(bucket_key_prefix)
    )


# train


output_path = "s3://{0}/{1}/output".format(bucket_name, bucket_key_prefix)
code_location = "s3://{0}/{1}/code".format(bucket_name, bucket_key_prefix)

m = MXNet(
    "sms_spam_classifier_mxnet_script.py",
    role=role,
    train_instance_count=1,
    train_instance_type="ml.c5.2xlarge",
    output_path=output_path,
    base_job_name="sms-spam-classifier-mxnet",
    framework_version="1.2",
    code_location=code_location,
    hyperparameters={"batch_size": 100, "epochs": 20, "learning_rate": 0.01},
    py_version="py3",
)

inputs = {
    "train": "s3://{0}/{1}/train/".format(bucket_name, bucket_key_prefix),
    "val": "s3://{0}/{1}/val/".format(bucket_name, bucket_key_prefix),
}

m.fit(inputs)


# deploy the model on sage maker endpoint

mxnet_pred = m.deploy(
    initial_instance_count=1,
    instance_type="ml.t2.medium",
    endpoint_name="sagemaker-endpoint",
)
