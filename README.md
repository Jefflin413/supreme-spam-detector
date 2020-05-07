# supreme-spam-detector

Chad version of the classic spam/ ham ML question.

1) Have a custom domain that you own with your own custom email address but don't have a spam filter on it? (Have a look at step 2, if you don't and are interested in getting one)
2) Do you know some basic ML?

Say. No. More. Fam

Here, I try to build an end to end pipeline using AWS services to create a spam classifier which works on any domain that you own. In other words, it was an attempt by me to recreate the spam classifiers which you find in gmail which can be actually deployed and used by me.

## Working
1) Send an email to the the email address belonging to your domain.![pic1](https://user-images.githubusercontent.com/20079387/81340762-61d74b80-907e-11ea-881c-166029e4caed.png)


2) Get back an email address from your domain to any of your personal email address informing you if the email was spam or not. ![pic2](https://user-images.githubusercontent.com/20079387/81340872-8fbc9000-907e-11ea-9e84-0691469c103b.png)


**Interested? Continue reading below on how to recreate it**

## What do you need?
1) AWS account
2) the custom domain to implement the spam classifier on 
3) Eso es!


## Step 1: build, train and deploy an ML spam classifier

You're free to build your own model. I chose one of the simplest datasets available. And used aws' [sagemaker]( ​https://aws.amazon.com/sagemaker) to train and deploy it. 

Credits: https://github.com/aws-samples/reinvent2018-srv404-lambda-sagemaker/blob/master/training/README.md

1) Create an S3 bucket which will get connected to your sagemaker. 
2) Create a Sagemaker notebook. 
3) Either build your own ML model on it or just copy and paste my files: `train_and_deploy_model.py` and `utilites.py`. Note: you will have to change some of the hardcoded names like that of the S3 bucket. 
4) Run the pasted files in case you end up using my code. This will train the model and deploy it as an endpoint on sagemaker. 

The dataset I use is [UCI's spam collection data set](https://archive.ics.uci.edu/ml/datasets/SMS+Spam+Collection) ![dataset](https://user-images.githubusercontent.com/20079387/81340386-c04ffa00-907d-11ea-9afc-516065b41adc.png)


## Step 2: hook up your custom domain with AWS

----
**Don't have your own custom domain? Are you a student? If yes, you can follow the steps that I took to get one for free**. 


**ignore if you already have a custom domain**

1) Sign up for [Github student education pack](https://education.github.com/pack)
2) Once, you register, you can get yourself a custom domain free for one year, sponsored by name.com ![pic_temp](https://user-images.githubusercontent.com/20079387/81337723-79f89c00-9079-11ea-886f-12018abcad6e.png)
3) Register your domain on it. 
4) Side note: feel free to host your github.io webpage on this domain using the [official github instructions](https://help.github.com/en/github/working-with-github-pages/configuring-a-custom-domain-for-your-github-pages-site). Github also provides free https on [the custom domains](https://github.blog/2018-05-01-github-pages-custom-domains-https/)
----

Now that you have the custom domain with your custom email address on it, you need to hook it up with your amazon SES. 

1) Go to [SES on AWS](https://aws.amazon.com/ses/). 
2) Click on Verify a domain. 
3) You will be provided with a TXT record that you'll need to add to your DNS settings. ![temp](https://user-images.githubusercontent.com/20079387/81338347-7b769400-907a-11ea-946a-ee6d647265bd.png)
4) Note: How to add this record will vary. Check your DNS provider for more info. 

**Now, we will tell AWS to receive an email for a custom email address that belongs to our domain**

5) Choose an email address which belongs to your domain. Add a record of the type MX in your DNS settings which links it to AWS s3. ![smtp](https://user-images.githubusercontent.com/20079387/81339172-bd540a00-907b-11ea-8e66-957c42021a41.png)
6) Add this email address in the "Email Receiving rule set" on the SES dashboard in AWS. 
7) Create tehe S3 bucket where the email will go whenever any email is sent to the email address you specified in step 4

## Step 3: Lambda function which is triggered when an email is sent

All we need to do now is create a lambda function, which gets triggered every time an object is inserted in the S3 bucket we created for receiving the email. 

1) Create the lambda function adding the S3 bucket as the trigger
2) Copy the `lambda.py` code in this lambda function. 
3) You will need to add a layer which allows `numpy` to be called  in this lambda function. Fortunately AWS provides a custom layer![temp2](https://user-images.githubusercontent.com/20079387/81339690-91855400-907c-11ea-85c7-52118e05f3ed.png)
4) Provide the necessary roles to the lambda function. (SES full access, S3 Full Access, Cloudwatch full access)

Note: As before, you will need to change some hard-coded information inside the lambda function. Be diligent, you fool!

The lambda function will send an email to the specified address using a pre-assigned email address belonging to your custom domain. 

That's it. 

## Architecture Diagram
![diagram](https://user-images.githubusercontent.com/20079387/81341680-f1312e80-907f-11ea-93ea-82106385600d.png)


### TODO

- [ ] Create a CloudFormation template (T1) to represent all the infrastructure resources (ex. Lambda, SES configuration, etc.) and permissions (IAM policies, roles, etc.).
 
