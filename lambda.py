import json
import numpy as np
from hashlib import md5
import boto3
import urllib.parse
import email

maketrans = str.maketrans
vocabulary_length = 9013

s3 = boto3.client("s3")
ses = boto3.client("ses")


def text_to_word_sequence(
    text, filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n', lower=True, split=" "
):
    """Converts a text to a sequence of words (or tokens).
    # Arguments
        text: Input text (string).
        filters: list (or concatenation) of characters to filter out, such as
            punctuation. Default: `!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n`,
            includes basic punctuation, tabs, and newlines.
        lower: boolean. Whether to convert the input to lowercase.
        split: str. Separator for word splitting.
    # Returns
        A list of words (or tokens).
    """
    if lower:
        text = text.lower()

    translate_dict = dict((c, split) for c in filters)
    translate_map = maketrans(translate_dict)
    text = text.translate(translate_map)

    seq = text.split(split)
    return [i for i in seq if i]


def vectorize_sequences(sequences, vocabulary_length):
    results = np.zeros((len(sequences), vocabulary_length))
    for i, sequence in enumerate(sequences):
        results[i, sequence] = 1.0
    return results


def one_hot_encode(messages, vocabulary_length):
    data = []
    for msg in messages:
        temp = one_hot(msg, vocabulary_length)
        data.append(temp)
    return data


def one_hot(
    text, n, filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n', lower=True, split=" "
):
    """One-hot encodes a text into a list of word indexes of size n.
    This is a wrapper to the `hashing_trick` function using `hash` as the
    hashing function; unicity of word to index mapping non-guaranteed.
    # Arguments
        text: Input text (string).
        n: int. Size of vocabulary.
        filters: list (or concatenation) of characters to filter out, such as
            punctuation. Default: `!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n`,
            includes basic punctuation, tabs, and newlines.
        lower: boolean. Whether to set the text to lowercase.
        split: str. Separator for word splitting.
    # Returns
        List of integers in [1, n]. Each integer encodes a word
        (unicity non-guaranteed).
    """
    return hashing_trick(
        text, n, hash_function="md5", filters=filters, lower=lower, split=split
    )


def hashing_trick(
    text,
    n,
    hash_function=None,
    filters='!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n',
    lower=True,
    split=" ",
):
    """Converts a text to a sequence of indexes in a fixed-size hashing space.
    # Arguments
        text: Input text (string).
        n: Dimension of the hashing space.
        hash_function: defaults to python `hash` function, can be 'md5' or
            any function that takes in input a string and returns a int.
            Note that 'hash' is not a stable hashing function, so
            it is not consistent across different runs, while 'md5'
            is a stable hashing function.
        filters: list (or concatenation) of characters to filter out, such as
            punctuation. Default: `!"#$%&()*+,-./:;<=>?@[\\]^_`{|}~\t\n`,
            includes basic punctuation, tabs, and newlines.
        lower: boolean. Whether to set the text to lowercase.
        split: str. Separator for word splitting.
    # Returns
        A list of integer word indices (unicity non-guaranteed).
    `0` is a reserved index that won't be assigned to any word.
    Two or more words may be assigned to the same index, due to possible
    collisions by the hashing function.
    The [probability](
        https://en.wikipedia.org/wiki/Birthday_problem#Probability_table)
    of a collision is in relation to the dimension of the hashing space and
    the number of distinct objects.
    """
    if hash_function is None:
        hash_function = hash
    elif hash_function == "md5":
        hash_function = lambda w: int(md5(w.encode()).hexdigest(), 16)

    seq = text_to_word_sequence(text, filters=filters, lower=lower, split=split)
    return [int(hash_function(w) % (n - 1) + 1) for w in seq]


def lambda_handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = urllib.parse.unquote_plus(
        event["Records"][0]["s3"]["object"]["key"], encoding="utf-8"
    )
    try:
        response = s3.get_object(Bucket=bucket, Key=key)["Body"]
        body = response.read()
        s = body.decode("utf-8")
        msg = email.message_from_string(s)
        body = ""

        if msg.is_multipart():
            for part in msg.walk():
                ctype = part.get_content_type()
                cdispo = str(part.get("Content-Disposition"))

                # skip any text/plain (txt) attachments
                if ctype == "text/plain" and "attachment" not in cdispo:
                    body = part.get_payload(decode=True)  # decode
                    break
        # not multipart - i.e. plain text, no attachments, keeping fingers crossed
        else:
            body = msg.get_payload(decode=True)
        sender = msg["from"]
        to = msg["to"]
        subject = msg["subject"]
        body = body.decode("utf-8")
        body = body.replace("\r", "")
        body = " ".join([word.lower() for word in body.split()])
        date = msg["date"]
        print(
            f"date: {date}\n to:{to}\nsender:{sender}\nsubject:{subject}\nbody:{body}"
        )
        runtime = boto3.client("runtime.sagemaker")
        ENDPOINT_NAME = "sagemaker-endpoint"
        message = body
        test_messages = [body]
        one_hot_test_messages = one_hot_encode(test_messages, vocabulary_length)
        encoded_test_messages = vectorize_sequences(
            one_hot_test_messages, vocabulary_length
        )
        body = json.dumps(encoded_test_messages.tolist())

        response = runtime.invoke_endpoint(
            EndpointName=ENDPOINT_NAME, ContentType="application/json", Body=body
        )

        x = response["Body"]
        y = x.read()
        print(y)
        s = y.decode("utf-8")
        s = json.loads(s)
        label = int(s["predicted_label"][0][0])
        probability = s["predicted_probability"][0][0]
        if label == 1:
            label = "spam"
        else:
            label = "ham"
        print(label, probability)
        body = f"""We have received your email sent at {date} with the subject: 
{subject}. 

Here is a 240 character sample of the email body:
{message[:240]}
        
The email was classified as {label} with a {probability} confidence """
        ses.send_email(
            Destination={"ToAddresses": ["xyz@columbia.edu",],},
            Message={
                "Body": {"Text": {"Charset": "UTF-8", "Data": body,},},
                "Subject": {"Charset": "UTF-8", "Data": subject,},
            },
            Source="test@domain.com",
        )
    except Exception as e:
        print(e)
