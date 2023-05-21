KEY_NAME="cloud-ex1-`date +'%N'`"
KEY_PEM="$KEY_NAME.pem"
SEC_GRP="my-sg-`date +'%N'`"
UBUNTU_20_04_AMI="ami-042e8287309f5df03"

# set the region for the machine
export AWS_REGION=us-east-1

#create a key-pair
echo "create key pair $KEY_PEM to connect to instances and save locally"
aws ec2 create-key-pair --key-name $KEY_NAME \
    | jq -r ".KeyMaterial" > $KEY_PEM

# secure the key pair
chmod 400 $KEY_PEM 

# create security group
echo "setup firewall $SEC_GRP"
aws ec2 create-security-group   \
    --group-name $SEC_GRP       \
    --description "Access my instances" 

# get my IP for the rules and more
MY_IP=$(curl ipinfo.io/ip)
echo "My IP: $MY_IP"

# setup rules for HTTP and SSH
echo "setup rule allowing SSH access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 22 --protocol tcp \
    --cidr $MY_IP/32

echo "setup rule allowing HTTP (port 5000) access to $MY_IP only"
aws ec2 authorize-security-group-ingress        \
    --group-name $SEC_GRP --port 5000 --protocol tcp \
    --cidr $MY_IP/32

# Create instance
echo "Creating Ubuntu 20.04 instance..."
RUN_INSTANCES=$(aws ec2 run-instances   \
    --image-id $UBUNTU_20_04_AMI        \
    --instance-type t3.micro            \
    --key-name $KEY_NAME                \
    --security-groups $SEC_GRP)

INSTANCE_ID=$(echo $RUN_INSTANCES | jq -r '.Instances[0].InstanceId')

# wait for instance creation
echo "Waiting for instance creation..."
aws ec2 wait instance-running --instance-ids $INSTANCE_ID

# get instance IP
PUBLIC_IP=$(aws ec2 describe-instances  --instance-ids $INSTANCE_ID | 
    jq -r '.Reservations[0].Instances[0].PublicIpAddress'
)

echo "New instance $INSTANCE_ID @ $PUBLIC_IP"

# deploy code using the key-pair
echo "deploying code to production"
scp -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=60" app.py requirements.txt ubuntu@$PUBLIC_IP:/home/ubuntu/

# configure flask environment variables
export FLASK_APP=app

# install python requirments for machine
echo "setup production environment"
ssh -i $KEY_PEM -o "StrictHostKeyChecking=no" -o "ConnectionAttempts=10" ubuntu@$PUBLIC_IP <<EOF
    sudo apt update
    sudo apt install python3-pip -y
    sudo apt install python3-flask -y
    sudo pip3 install -r requirements.txt 
    # run app
    nohup flask run --host 0.0.0.0  &>/dev/null &
    exit
EOF

# check application is accessiable
echo "test that it all worked"
curl  --retry-connrefused --retry 10 --retry-delay 1  http://$PUBLIC_IP:5000
