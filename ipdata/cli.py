import csv
import json
import os
import sys
from ipaddress import ip_address
from pathlib import Path
from sys import stderr, stdout

import click

if __name__ == '__main__':
    from ipdata import IPData
else:
    from .ipdata import IPData


class WrongAPIKey(Exception):
    pass


class IPAddressType(click.ParamType):
    name = 'IP_Address'

    def convert(self, value, param, ctx):
        try:
            return ip_address(value)
        except:
            self.fail(f'{value} is not valid IPv4 or IPv6 address')

    def __str__(self) -> str:
        return 'IP Address'


@click.group(help='CLI for IPData API', invoke_without_command=True)
@click.option('--api-key', required=False, default=None, help='IPData API Key')
@click.pass_context
def cli(ctx, api_key):
    ctx.ensure_object(dict)
    ctx.obj['api-key'] = get_and_check_api_key(api_key)
    if ctx.invoked_subcommand is None:
        print_ip_info(api_key)
    else:
        pass


def get_api_key_path():
    home = str(Path.home())
    return os.path.join(home, '.ipdata')


def get_api_key():
    key_path = get_api_key_path()
    if os.path.exists(key_path):
        with open(key_path, 'r') as f:
            for line in f:
                if line:
                    return line
    else:
        return None


def get_and_check_api_key(api_key: str = None) -> str:
    if api_key is None:
        api_key = get_api_key()
    if api_key is None:
        print(f'Please specify IPData API Key', file=stderr)
        raise WrongAPIKey
    return api_key


@cli.command()
@click.argument('api-key', required=True, type=str)
def init(api_key):
    key_path = get_api_key_path()

    ipdata = IPData(api_key)
    res = ipdata.lookup('8.8.8.8')
    if res['status'] == 200:
        existing_api_key = get_api_key()
        if existing_api_key:
            print(f'Warning: You already have an IPData API Key "{existing_api_key}" listed in {key_path}. '
                  f'It will be overwritten with {api_key}',
                  file=stderr)

        with open(key_path, 'w') as f:
            f.write(api_key)
        print(f'New API Key is saved to {key_path}')
    else:
        print(f'Failed to check the API Key (Error: {res["status"]}): {res["message"]}',
              file=stderr)


def json_filter(json, fields):
    res = dict()
    for name in fields:
        if name in json:
            res[name] = json[name]
        elif name.find('.') != -1:
            parts = name.split('.')
            part = parts[0] if len(parts) > 1 else None
            if part and part in json:
                sub_value = json_filter(json[part], ('.'.join(parts[1:]), ))
                if isinstance(sub_value, dict):
                    if part not in res:
                        res[part] = sub_value
                    else:
                        res[part] = {**res[part], **sub_value}
                else:
                    res[part] = sub_value
        else:
            pass
    return res


@cli.command()
@click.option('--fields', required=False, type=str, default=None, help='Coma separated list of fields to extract')
@click.pass_context
def me(ctx, fields):
    print_ip_info(ctx.obj['api-key'], ip=None, fields=fields.split(',') if fields else None)


@cli.command()
@click.argument('ip-list', required=True, type=click.File(mode='r', encoding='utf-8'))
@click.option('--output', required=False, default=stdout, type=click.File(mode='w', encoding='utf-8'),
              help='Output to file or stdout')
@click.option('--output-format', required=False, type=click.Choice(('JSON', 'CSV'), case_sensitive=False), default='JSON',
              help='Format of output')
@click.option('--fields', required=False, type=str, default=None, help='Coma separated list of fields to extract')
@click.pass_context
def batch(ctx, ip_list, output, output_format, fields):
    extract_fields = fields.split(',') if fields else None

    if output_format == 'CSV' and extract_fields is None:
        print(f'Output in CSV format is not supported without specification of exactly fields to extract '
              f'because of plain nature of CSV format. Please use JSON format instead.', file=stderr)
        return

    result_context = {}
    if output_format == 'CSV':
        print(f'# {fields}', file=output)  # print comment with columns
        result_context['writer'] = csv.writer(output)

        def print_result(res):
            result_context['writer'].writerow([res[k] for k in extract_fields])

        def finish():
            pass

    elif output_format == 'JSON':
        result_context['results'] = []

        def print_result(res):
            result_context['results'].append(res)

        def finish():
            json.dump(result_context, fp=output)

    else:
        print(f'Unsupported format: {output_format}', file=stderr)
        return

    for ip in ip_list:
        ip = ip.strip()
        if len(ip) > 0:
            print_result(get_ip_info(ctx.obj['api-key'], ip=ip.strip(), fields=extract_fields))
    finish()


@click.command()
@click.argument('ip', required=True, type=IPAddressType())
@click.option('--fields', required=False, type=str, default=None, help='Coma separated list of fields to extract')
@click.option('--api-key', required=False, default=None, help='IPData API Key')
def ip(ip, fields, api_key):
    print_ip_info(get_and_check_api_key(api_key),
                  ip=ip, fields=fields.split(',') if fields else None)


def print_ip_info(api_key, ip=None, fields=None):
    try:
        json.dump(get_ip_info(api_key, ip, fields), stdout)
    except ValueError as e:
        print(f'Error: IP address {e}', file=stderr)


def get_ip_info(api_key, ip=None, fields=None):
    ip_data = IPData(get_and_check_api_key(api_key))
    if ip:
        res = ip_data.lookup(ip)
    else:
        res = ip_data.lookup()
    if fields and len(fields) > 0:
        return json_filter(res, fields)
    else:
        return res


def lookup_field(data, field):
    if field in data:
        return field, data[field]
    elif '.' in field:
        parent, children = field.split('.')
        parent_field, parent_data = lookup_field(data, parent)
        if parent_field:
            children_field, children_data = lookup_field(parent_data, children)
            return parent_field, {parent_field: children_data}
    return None, None


# @cli.command()
# @click.argument('ip', type=str)
# @click.argument('fields', type=str, nargs=-1)
# @click.option('--api_key', required=False, default=None, help='IPData API Key')
# def ip(ip, fields, api_key):
#     print_ip_info(api_key, ip, fields)


@cli.command()
@click.pass_context
def info(ctx):
    res = IPData(get_and_check_api_key(ctx.obj['api-key'])).lookup('8.8.8.8')
    print(f'Number of requests made: {res["count"]}')


def is_ip_address(value):
    try:
        ip_address(value)
        return True
    except ValueError:
        return False


def todo():
    if len(sys.argv) >= 2 and is_ip_address(sys.argv[1]):
        ip()
    else:
        cli(obj={})


if __name__ == '__main__':
    todo()
