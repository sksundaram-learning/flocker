# Converted from EC2InstanceSample.template located at:
# http://aws.amazon.com/cloudformation/aws-cloudformation-templates/

from troposphere import FindInMap, GetAtt, Base64, Join
from troposphere import Parameter, Output, Ref, Template, GetAZs, Select
import troposphere.ec2 as ec2

OWNER = u"richardw"
NUM_NODES = 2
NODE_NAME_TEMPLATE = u"{owner}flockerdemo{index}"

# TODO: Fix control-service IP
AGENT_YAML_TEMPLATE = """\
control-service:
    hostname: "${control_service_ip}"
    port: 4524
dataset:
    backend: "aws"
    region: "${aws_region}"
    zone: "${aws_zone}"
    access_key_id: "${access_key_id}"
    secret_access_key: "${secret_access_key}"
version: 1
"""

template = Template()

keyname_param = template.add_parameter(Parameter(
    "KeyName",
    Description="Name of an existing EC2 KeyPair to enable SSH "
                "access to the instance",
    Type="String",
))

access_key_id_param = template.add_parameter(Parameter(
    "AccessKeyID",
    Description="Your Amazon AWS access key ID",
    Type="String",
))

secret_access_key_param = template.add_parameter(Parameter(
    "SecretAccessKey",
    Description="Your Amazon AWS secret access key.",
    Type="String",
))

template.add_mapping('RegionMap', {
    # richardw-test1 AMI generated from a running acceptance test node.
    "us-east-1":      {"AMI": "ami-6cabe306"},
})

instances = []
zone = Select(0, GetAZs(""))

for i in range(NUM_NODES):
    node_name = NODE_NAME_TEMPLATE.format(owner=OWNER, index=i)
    ec2_instance = ec2.Instance(
        node_name,
        ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "AMI"),
        InstanceType="m3.large",
        KeyName=Ref(keyname_param),
        SecurityGroups=["acceptance"],
        AvailabilityZone=zone,
    )
    if i == 0:
        control_service_ip = '127.0.0.1'
        control_service_instance = ec2_instance
    else:
        control_service_ip = GetAtt(control_service_instance, "PublicIp")
    ec2_instance.UserData = Base64(Join("", [
        '#!/bin/bash\n',
        'control_service_ip="', control_service_ip, '"\n',
        'aws_region="', Ref("AWS::Region"), '"\n',
        'aws_zone="', zone, '"\n',
        'access_key_id="', Ref(access_key_id_param), '"\n',
        'secret_access_key="', Ref(secret_access_key_param), '"\n',
        'cat <<EOF >/etc/flocker/agent.yml\n',
        AGENT_YAML_TEMPLATE,
        'EOF\n'
        ]))
    template.add_resource(ec2_instance)
    template.add_output([
        Output(
            "{}PublicIP".format(node_name),
            Description="Public IP address of the newly created EC2 instance",
            Value=GetAtt(ec2_instance, "PublicIp"),
        ),
        Output(
            "{}PublicDNS".format(node_name),
            Description="Public DNSName of the newly created EC2 instance",
            Value=GetAtt(ec2_instance, "PublicDnsName"),
        ),
    ])

template.add_output([
    Output(
        "AvailabilityZone",
        Description="Availability Zone of the newly created EC2 instance",
        Value=Ref("AWS::Region"),
    ),
])

print(template.to_json())
