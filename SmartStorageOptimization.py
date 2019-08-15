import boto3
import sys
from datetime import datetime, timedelta
import pprint
import json
from decimal import Decimal
from pulp import*
prob = LpProblem("volumeCost", LpMinimize)
import subprocess
import paramiko
import math

#Initial user input
print('Welcome! Please enter information below.')
region = input('region: ')
if(region==''):
    print('Please input region.')
    region= input('region: ')
InstanceId = input('Instance Id: ')
if(InstanceId==''):
    print('Please input Instance Id.')
    InstanceId= input('Instance Id: ')
Passwd= input('Password: ')
if(Passwd==''):
    print('Please input password.')
    Passwd= input('Password: ')


    
def main():
    """collects cloudwatch metrics and puts them in a Dyanmodb table"""
    cloudwatch = boto3.client('cloudwatch', region_name= region)

    readbytes = cloudwatch.get_metric_statistics(
        Period = 120,
        StartTime= datetime.now() - timedelta(seconds=600),
        EndTime= datetime.now(),
        MetricName= 'VolumeWriteOps',
        Namespace= 'AWS/EBS',
        Statistics = ['Average'],
        Dimensions=[{'Name':'VolumeId', 'Value':l['Ebs']['VolumeId']}]
        )
    dict_2_len = len(readbytes['Datapoints'])
    global averages2
    averages2=[]
    global times
    times = []
    while dict_2_len != 0:
        averages2 += [readbytes['Datapoints'][dict_2_len-1]['Average']]
        times += [readbytes['Datapoints'][dict_2_len-1]['Timestamp']]
        dict_2_len -=1

    idletime = cloudwatch.get_metric_statistics(
        Period = 120,
        StartTime= datetime.now() - timedelta(seconds=600),
        EndTime= datetime.now(),
        MetricName= 'VolumeIdleTime',
        Namespace= 'AWS/EBS',
        Statistics = ['Average'],
        Dimensions=[{'Name':'VolumeId', 'Value':l['Ebs']['VolumeId']}]
        )
    dict_3_len = len(idletime['Datapoints'])
    global averages3
    averages3=[]
    while dict_3_len != 0:
        averages3 += [idletime['Datapoints'][dict_3_len-1]['Average']]
        dict_3_len -=1

    burstbalance = cloudwatch.get_metric_statistics(
        Period = 120,
        StartTime= datetime.now() - timedelta(seconds=600),
        EndTime= datetime.now(),
        MetricName= 'BurstBalance',
        Namespace= 'AWS/EBS',
        Statistics = ['Average'],
        Dimensions=[{'Name':'VolumeId', 'Value':l['Ebs']['VolumeId']}]
        )
    dict_4_len = len(burstbalance['Datapoints'])
    global averages4
    averages4=[]
    while dict_4_len != 0:
        averages4 += [burstbalance['Datapoints'][dict_4_len-1]['Average']]
        dict_4_len -=1

    writeOps = cloudwatch.get_metric_statistics(
        Period = 120,
        StartTime= datetime.now() - timedelta(seconds=600),
        EndTime= datetime.now(),
        MetricName= 'VolumeWriteOps',
        Namespace= 'AWS/EBS',
        Statistics = ['Average'],
        Dimensions=[{'Name':'VolumeId', 'Value':l['Ebs']['VolumeId']}]
        )
    dict_9_len = len(writeOps['Datapoints'])
    global averages9
    averages9=[]
    while dict_9_len != 0:
        averages9 += [writeOps['Datapoints'][dict_9_len-1]['Average']]
        dict_9_len -=1

    readOps = cloudwatch.get_metric_statistics(
        Period = 120,
        StartTime= datetime.now() - timedelta(seconds=600),
        EndTime= datetime.now(),
        MetricName= 'VolumeReadOps',
        Namespace= 'AWS/EBS',
        Statistics = ['Average'],
        Dimensions=[{'Name':'VolumeId', 'Value':l['Ebs']['VolumeId']}]
        )
    dict_10_len = len(writeOps['Datapoints'])
    global averages10
    averages10=[]
    while dict_10_len != 0:
        averages10 += [readOps['Datapoints'][dict_10_len-1]['Average']]
        dict_10_len -=1

    CPUuse = cloudwatch.get_metric_statistics(
        Period = 120,
        StartTime= datetime.now() - timedelta(seconds=600),
        EndTime= datetime.now(),
        MetricName= 'CPUUtilization',
        Namespace= 'AWS/EC2',
        Statistics = ['Average'],
        Dimensions=[
            {'Name':'InstanceId', 'Value': InstanceId}]
        )
    dict_5_len = len(CPUuse['Datapoints'])
    global averages5
    averages5=[]
    while dict_5_len != 0:
        averages5 += [CPUuse['Datapoints'][dict_5_len-1]['Average']]
        dict_5_len -=1


    times =[time.strftime("%B %d %Y %I:%M %p") for time in times]
    averages2 = [int(average2) for average2 in averages2]
    averages3 = [int(average3) for average3 in averages3]
    averages4 = [int(average4) for average4 in averages4]
    averages5 = [Decimal(average5) for average5 in averages5]
    averages5 = [round(average5, 3) for average5 in averages5]
    averages9 = [int(average9) for average9 in averages9]
    averages10 = [int(average10) for average10 in averages10]

    # Get the service resource.
    dynamodb_client = boto3.client('dynamodb')
    table_name=l['Ebs']['VolumeId']
    existing_tables=dynamodb_client.list_tables()['TableNames']
    
    #Creates the DynamoDB table if not already existing
    if table_name not in existing_tables:
        print('Table does not exist for this volume.')
        print('Please wait, creating new table...')
        table = dynamodb_client.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'Time',
                    'KeyType': 'HASH'
                },
                {
                    'AttributeName': 'VolumeReadOps',
                    'KeyType': 'RANGE'
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'Time',
                    'AttributeType': 'S'
                },
                {
                    'AttributeName': 'VolumeReadOps',
                    'AttributeType': 'N'
                },
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
    else:
        print('Table already exists, adding data...')
    
    # Wait until the table exists.
    
    dynamodb=boto3.resource('dynamodb')
    table = dynamodb.Table(l['Ebs']['VolumeId'])
    table.meta.client.get_waiter('table_exists').wait(TableName=l['Ebs']['VolumeId'])
    
    #Puts the items in the table
    x = len(times)
    while x != 0:
        response = table.put_item(
            Item={
                'Time' : times[x-1],
                'VolumeWriteBytes' : averages2[x-1],
                'VolumeIdleTime' : averages3[x-1],
                'BurstBalance' : averages4[x-1],
                'CPUUtilization' : averages5[x-1],
                'VolumeReadOps' : averages10[x-1],
                'MaxOps' : averages9[x-1] + averages10[x-1]
                }
            )
        x-=1
    print('putitems succeeded')

#SSH
ec2=boto3.resource('ec2')
instance=ec2.Instance(InstanceId)
user_name = 'ec2-user'
passwd= Passwd
ip=instance.public_ip_address
ssh_client=paramiko.SSHClient()
ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh_client.connect(hostname= ip, username=user_name, password=passwd)
cmd='df -hT'
stdin,stdout,stderr=ssh_client.exec_command(cmd)
stdout=stdout.readlines()
s=list(stdout)
Filesystems= []
Mounts = []
Used = []
Use = []
for i in range(1, len(s)):
    if('tmpfs' not in s[i]):
        q=s[i].split()
        f= q[0]
        m= q[len(q)-1]
        u= q[3]
        us= q[5]       
        Filesystems += [f]
        Mounts += [m]
        Used += [u]
        Use += [us]

#Displays the information collected
ec2 = boto3.resource('ec2', region_name='us-east-2')
instance = ec2.Instance(InstanceId)
bdm = instance.block_device_mappings
global x
x=len(bdm)
space_needed=0
total_space=0
max_iops = 0
cost=0
print('The number of volumes attached to this instance is: ', x, '\n')
costs= {'gp2':0.1, 'st1':0.045, 'sc1':0.025}
while x != 0:
    l= dict(bdm[x-1])
    print('Device: ' + l['DeviceName'])
    print('Filesystem: ' + Filesystems[x-1])
    print('Mount: ' + Mounts[x-1])
    print('VolumeId: ' + l['Ebs']['VolumeId'])
    print('Status: ' + l['Ebs']['Status'])
    v= ec2.Volume(l['Ebs']['VolumeId'])
    print('Type: ' + v.volume_type)
    print('Total Space: ' + str(v.size) + 'GB')
    total_space += v.size
    main()
    print('Space Used: ' + Used[x-1][:len(Used[x-1])-1] + 'GB')
    space_needed += float(Used[x-1][:len(Used[x-1])-1])
    print('Max IOPS: ' + str(averages9[len(averages9)-1] + averages10[len(averages10)-1]))
    max_iops +=averages9[len(averages9)-1] + averages10[len(averages10)-1]
    print('Cost: $' + str(costs[v.volume_type]*v.size))
    cost += costs[v.volume_type]*v.size
    print('\n')
    x-=1

#Totals
print('The total space in this Instance is', total_space, 'GB')
print('The total spaced used in this Instance is', round(space_needed,2), 'GB')
print('The maximum IOPS of this Instance is', max_iops, 'IOPS')
print('The total cost of this storage configuration is $' + str(cost))

#Linear Model
volumes = ['gp2','st1','sc1'] #volume types

print("\nThe volumes to consider are:")
for v in volumes:
    print(v,end=', ')
    
#volume costs
costs = {'gp2':0.1, 'st1':0.045, 'sc1':0.025}


#volume gb
gbs = {'gp2':1, 'st1':1, 'sc1':1}


#max iops
maxops = {'gp2':16000, 'st1':500, 'sc1':250}


vol_vars = LpVariable.dicts("Volumes", volumes, 0, cat = "Integer")


prob += lpSum([costs[i]*vol_vars[i] for i in volumes])

#constraints
prob += lpSum([maxops[f] * vol_vars[f] for f in volumes]) >= max_iops, "IopsMinimum"
prob += lpSum([gbs[f]*vol_vars[f] for f in volumes]) >= math.ceil(space_needed) #gbmin round up?


prob.writeLP("volumeCost.lp")

#solving
prob.solve()
print("\nStatus:", LpStatus[prob.status])

print("The optimal (least cost) volume configuration consists of")
addition=0
for v in prob.variables():
    if v.name == 'Volumes_st1' or v.name == 'Volumes_sc1':
        if v.varValue<=250:
            addition += v.varValue
            v.varValue = 0
        if 250< v.varValue <500:
            v.varValue = 500
for v in prob.variables():
    if v.name == 'Volumes_gp2':
        v.varValue += addition
        if v.varValue <16:
            v.varValue=16
    if v.varValue>0:
        print(v.name, "=", v.varValue)
        

print("The total cost of this volume configuration is: ${}".format(round(value(prob.objective),2)))

if round(value(prob.objective), 2)>=cost:
    print('Your current storage configuration is optimal')
else:
    print('If you go with the storage configuration calculated above, you will save $' +str(cost -round(value(prob.objective), 2)))







