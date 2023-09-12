#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from aws_cdk import aws_ssm, core
from aws_cdk.aws_ec2 import (
    CfnRoute, CfnRouteTable, CfnSubnet, CfnSubnetRouteTableAssociation, CfnTransitGatewayAttachment, CfnVPC,
    CfnVPCEndpoint, Peer, Port, SecurityGroup, Vpc
)


def get_vpc(scope: core.Construct, configs: object):
    vpc_id = aws_ssm.StringParameter.value_from_lookup(scope, f'/{scope.env}/{configs["vpc_base_project"]}/vpc-id')
    vpc = Vpc.from_lookup(scope, 'vpc', vpc_id=vpc_id)
    # vpc = Vpc.from_vpc_attributes(scope, 'vpc', availability_zones=['ap-northeast-1a', 'ap-northeast-1c'], vpc_id=vpc_id)
    sg_dict = {}
    sagemaker_sg = SecurityGroup(scope,
        id=f'{scope.system}-security-sagemaker',
        vpc=vpc,
        security_group_name=f'{scope.system}-security-sagemaker',
        description=f'security group for sagemaker'
    )
    core.Tags.of(sagemaker_sg).add('Name', f'{scope.system}-security-sagemaker')
    for ingress_port in configs['sg_sagemaker_ingress_ports']:
        sagemaker_sg.add_ingress_rule(
            peer=Peer.ipv4(configs['cidr']),
            connection=Port.tcp(ingress_port['port'])
        )
    sg_dict['sagemaker'] = sagemaker_sg
    return vpc, sg_dict


def create_vpc(scope: core.Construct, configs: object):

    # VPC
    cfnvpc = CfnVPC(
        scope, f'{scope.system}-vpc',
        cidr_block=configs['cidr'],
        enable_dns_hostnames=True,
        enable_dns_support=True
    )
    core.Tags.of(cfnvpc).add('Name', f'{scope.system}-vpc')
    cidr = configs['cidr'].split('/')[-1]
    assert cidr in ['16', '24']
    ips = configs['cidr'].split('.')

    # PrivateSubnetA
    private_subnet_a = CfnSubnet(
        scope, f'{scope.system}-private-1',
        vpc_id=cfnvpc.ref,
        cidr_block=f'{ips[0]}.{ips[1]}.0.0/24' if cidr == '16' else f'{ips[0]}.{ips[1]}.{ips[2]}.128/27',
        availability_zone='ap-northeast-1a',
    )
    core.Tags.of(private_subnet_a).add('Name', f'{scope.system}-private-1')
    # PrivateSubnetC
    private_subnet_c = CfnSubnet(
        scope, f'{scope.system}-private-2',
        vpc_id=cfnvpc.ref,
        cidr_block=f'{ips[0]}.{ips[1]}.1.0/24' if cidr == '16' else f'{ips[0]}.{ips[1]}.{ips[2]}.160/27',
        availability_zone='ap-northeast-1c',
    )
    core.Tags.of(private_subnet_c).add('Name', f'{scope.system}-private-2')
    # TGWPrivateSubnetA
    tgw_private_subnet_a = CfnSubnet(
        scope, f'{scope.system}-tgw-private-1',
        vpc_id=cfnvpc.ref,
        cidr_block=f'{ips[0]}.{ips[1]}.255.0/28' if cidr == '16' else f'{ips[0]}.{ips[1]}.{ips[2]}.224/28',
        availability_zone='ap-northeast-1a',
    )
    core.Tags.of(tgw_private_subnet_a).add('Name', f'{scope.system}-tgw-private-1')
    # TGWPrivateSubnetC
    tgw_private_subnet_c = CfnSubnet(
        scope, f'{scope.system}-tgw-private-2',
        vpc_id=cfnvpc.ref,
        cidr_block=f'{ips[0]}.{ips[1]}.255.16/28' if cidr == '16' else f'{ips[0]}.{ips[1]}.{ips[2]}.240/28',
        availability_zone='ap-northeast-1c',
    )
    core.Tags.of(tgw_private_subnet_c).add('Name', f'{scope.system}-tgw-private-2')

    tgw_attachment = CfnTransitGatewayAttachment(scope, f'{scope.system}-tgw-attachment',
        vpc_id=cfnvpc.ref,
        subnet_ids=[tgw_private_subnet_a.ref, tgw_private_subnet_c.ref],
        transit_gateway_id=configs['transit_gateway_id']
    )
    core.Tags.of(tgw_attachment).add('Name', f'{scope.system}-tgw-attachment')
    core.Tags.of(tgw_attachment).add('Project', f'{scope.Project}')

    route_table = CfnRouteTable(scope, f'{scope.system}-private-route-table',
        vpc_id=cfnvpc.ref
    )
    core.Tags.of(route_table).add('Name', f'{scope.system}-private-route-table')
    CfnSubnetRouteTableAssociation(
        scope, 'private_route_table_association_a',
        route_table_id=route_table.ref,
        subnet_id=private_subnet_a.ref
    )
    CfnSubnetRouteTableAssociation(
        scope, 'private_route_table_association_c',
        route_table_id=route_table.ref,
        subnet_id=private_subnet_c.ref
    )
    CfnSubnetRouteTableAssociation(
        scope, 'tgw_route_table_association_a',
        route_table_id=route_table.ref,
        subnet_id=tgw_private_subnet_a.ref
    )
    CfnSubnetRouteTableAssociation(
        scope, 'tgw_route_table_association_c',
        route_table_id=route_table.ref,
        subnet_id=tgw_private_subnet_c.ref
    )
    cfn_route = CfnRoute(
        scope, 'private_route',
        route_table_id=route_table.ref,
        destination_cidr_block='0.0.0.0/0',
        transit_gateway_id=tgw_attachment.transit_gateway_id
    )
    cfn_route.add_depends_on(tgw_attachment)

    vpc = Vpc.from_vpc_attributes(scope, 'vpc', availability_zones=['ap-northeast-1a', 'ap-northeast-1c'], vpc_id=cfnvpc.ref)

    vpce_s3 = CfnVPCEndpoint(scope, 'vpce-s3', vpc_id=cfnvpc.ref, service_name=f'com.amazonaws.{scope.region}.s3', route_table_ids=[route_table.ref])
    # https://github.com/aws-cloudformation/cloudformation-coverage-roadmap/issues/350
    core.Tags.of(vpce_s3).add('Name', f'{scope.system}-vpce-s3')
    core.Tags.of(vpce_s3).add('Project', f'{scope.Project}')

    # security group
    sg_dict = {}

    # for sagemaker
    sagemaker_sg = SecurityGroup(scope,
        id=f'{scope.system}-security-sagemaker',
        vpc=vpc,
        security_group_name=f'{scope.system}-security-sagemaker',
        description=f'security group for sagemaker'
    )
    core.Tags.of(sagemaker_sg).add('Name', f'{scope.system}-security-sagemaker')
    for ingress_port in configs['sg_sagemaker_ingress_ports']:
        sagemaker_sg.add_ingress_rule(
            peer=Peer.ipv4(configs['cidr']),
            connection=Port.tcp(ingress_port['port'])
        )
    sg_dict['sagemaker'] = sagemaker_sg

    # for cloud9
    vpce_sg = SecurityGroup(scope,
        id=f'{scope.system}-algorithm-sg',
        vpc=vpc,
        security_group_name=f'{scope.system}-algorithm-vpce',
        description=f'security group for vpce'
    )
    vpce_sg.add_ingress_rule(
        peer=Peer.ipv4(configs['cidr']),
        connection=Port.tcp(443)
    )
    sg_dict['vpce'] = vpce_sg
    vpce_ssm = CfnVPCEndpoint(scope, 'vpce-ssm', vpc_id=cfnvpc.ref, service_name=f'com.amazonaws.{scope.region}.ssm', subnet_ids=[private_subnet_a.ref, private_subnet_c.ref], security_group_ids=[vpce_sg.security_group_id], vpc_endpoint_type='Interface', private_dns_enabled=True)
    core.Tags.of(vpce_ssm).add('Name', f'{scope.system}-vpce-ssm')
    core.Tags.of(vpce_ssm).add('Project', f'{scope.Project}')
    vpce_ssmmessages = CfnVPCEndpoint(scope, 'vpce-ssmmessages', vpc_id=cfnvpc.ref, service_name=f'com.amazonaws.{scope.region}.ssmmessages', subnet_ids=[private_subnet_a.ref, private_subnet_c.ref], security_group_ids=[vpce_sg.security_group_id], vpc_endpoint_type='Interface', private_dns_enabled=True)
    core.Tags.of(vpce_ssmmessages).add('Name', f'{scope.system}-vpce-ssmmessages')
    core.Tags.of(vpce_ssmmessages).add('Project', f'{scope.Project}')
    vpce_ec2messages = CfnVPCEndpoint(scope, 'vpce-ec2messages', vpc_id=cfnvpc.ref, service_name=f'com.amazonaws.{scope.region}.ec2messages', subnet_ids=[private_subnet_a.ref, private_subnet_c.ref], security_group_ids=[vpce_sg.security_group_id], vpc_endpoint_type='Interface', private_dns_enabled=True)
    core.Tags.of(vpce_ec2messages).add('Name', f'{scope.system}-vpce-ec2messages')
    core.Tags.of(vpce_ec2messages).add('Project', f'{scope.Project}')

    return vpc, sg_dict
