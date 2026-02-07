def get_policy(bucket_name):
    # policy sets the appropriate bucket as world readable (no write)
    # See the following good summary of Bucket Policies
    # https://gist.github.com/krishnasrinivas/2f5a9affe6be6aff42fe723f02c86d6a
    policy = {"Version": "2012-10-17",
              "Statement": [
                  {
                      "Sid": "",
                      "Effect": "Allow",
                      "Principal": {"AWS": "*"},
                      "Action": "s3:GetBucketLocation",
                      "Resource": f"arn:aws:s3:::{bucket_name}"
                  },
                  {
                      "Sid": "",
                      "Effect": "Allow",
                      "Principal": {"AWS": "*"},
                      "Action": "s3:ListBucket",
                      "Resource": f"arn:aws:s3:::{bucket_name}"
                  },
                  {
                      "Sid": "",
                      "Effect": "Allow",
                      "Principal": {"AWS": "*"},
                      "Action": "s3:GetObject",
                      "Resource": f"arn:aws:s3:::{bucket_name}/*"
                  }
              ]}

    return policy
