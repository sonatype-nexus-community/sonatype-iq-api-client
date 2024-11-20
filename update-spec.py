#
# Copyright 2019-Present Sonatype Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import requests
import sys

from yaml import dump as yaml_dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper

if len(sys.argv) != 3:
    print(f'Usage: {sys.argv[0]} <IQ_SERVER_URL> <IQ_SERVER_VERSION>')
    sys.exit(0)

IQ_SERVER_URL = sys.argv[1]
IQ_SPEC_PATH = '/api/v2/endpoints/public'
IQ_VERSION = sys.argv[2]

json_spec_response = requests.get(f'{IQ_SERVER_URL}{IQ_SPEC_PATH}')
json_spec = json_spec_response.json()

# Add OpenAPI Info Block
if 'info' not in json_spec:
    print('Adding `info`')
    json_spec['info'] = {
        'title': 'Sonatype IQ Server',
        'description': 'This documents the available APIs into [Sonatype IQ Server]'
                       '(https://www.sonatype.com/products/open-source-security-dependency-management).',
        'contact': {
            'name': 'Sonatype Community Maintainers',
            'url': 'https://github.com/sonatype-nexus-community'
        },
        'license': {
            'name': 'Apache 2.0',
            'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'
        },
        'version': IQ_VERSION
    }

# Add `securitySchemes` under `components`
if 'components' in json_spec and 'securitySchemes' not in json_spec['components']:
    print('Adding `securitySchemes`...')
    json_spec['components']['securitySchemes'] = {
        'BasicAuth': {
            'type': 'http',
            'scheme': 'basic'
        }
    }
if 'security' not in json_spec:
    json_spec['security'] = [
        {
            'BasicAuth': []
        }
    ]

# Fix Response schema for GET /api/v2/applications
if 'paths' in json_spec and '/api/v2/applications' in json_spec['paths']:
    if 'get' in json_spec['paths']['/api/v2/applications']:
        print('Fixing GET /api/v2/application...')
        json_spec['paths']['/api/v2/applications']['get']['responses'] = {
            'default': {
                'description': 'default response',
                'content': {
                    'application/json': {
                        'schema': {
                            '$ref': '#/components/schemas/ApiApplicationListDTO'
                        }
                    }
                }
            }
        }

# Add schemas for /api/v2/config
if 'components' in json_spec and 'schemas' in json_spec['components'] \
        and 'SystemConfig' not in json_spec['components']:
    print('Injecting schema: SystemConfigProperty...')
    json_spec['components']['schemas']['SystemConfigProperty'] = {
        'type': 'string',
        'enum': [
            'baseUrl',
            'forceBaseUrl'
        ]
    }

    print('Injecting schema: SystemConfig...')
    json_spec['components']['schemas']['SystemConfig'] = {
        'properties': {
            'baseUrl': {
                'nullable': True,
                'type': 'string'
            },
            'forceBaseUrl': {
                'nullable': True,
                'type': 'boolean'
            }
        }
    }

# Fix Response schema for GET /api/v2/config
if 'paths' in json_spec and '/api/v2/config' in json_spec['paths']:
    if 'delete' in json_spec['paths']['/api/v2/config']:
        print('Fixing DELETE /api/v2/config...')
        json_spec['paths']['/api/v2/config']['delete']['parameters'][0].update({
            'schema': {
                'items': {
                    '$ref': '#/components/schemas/SystemConfigProperty'
                },
                'type': 'array',
                'uniqueItems': True
            }
        })
        json_spec['paths']['/api/v2/config']['delete']['responses'] = {
            204: {
                'description': 'System Configuration removed',
                'content': {}
            }
        }

    if 'get' in json_spec['paths']['/api/v2/config']:
        print('Fixing GET /api/v2/config...')
        json_spec['paths']['/api/v2/config']['get']['parameters'][0].update({
            'schema': {
                'items': {
                    '$ref': '#/components/schemas/SystemConfigProperty'
                },
                'type': 'array',
                'uniqueItems': True
            }
        })
        json_spec['paths']['/api/v2/config']['get']['responses'] = {
            200: {
                'description': 'System Configuration retrieved',
                'content': {
                    'application/json': {
                        'schema': {
                            '$ref': '#/components/schemas/SystemConfig'
                        }
                    }
                }
            }
        }
    if 'put' in json_spec['paths']['/api/v2/config']:
        print('Fixing GET /api/v2/config...')
        json_spec['paths']['/api/v2/config']['put']['requestBody'] = {
            'content': {
                'application/json': {
                    'schema': {
                        '$ref': '#/components/schemas/SystemConfig'
                    }
                }
            }
        }
        json_spec['paths']['/api/v2/config']['put']['responses'] = {
            204: {
                'description': 'System Configuration updated',
                'content': {}
            }
        }

# Fix `ApiComponentDetailsDTOV2` schema
if 'components' in json_spec and 'schemas' in json_spec['components'] \
        and 'ApiComponentDetailsDTOV2' in json_spec['components']['schemas']:
    print('Fixing schema: ApiComponentDetailsDTOV2...')
    new_api_component_details_dto_v2 = json_spec['components']['schemas']['ApiComponentDetailsDTOV2']

    new_api_component_details_dto_v2['properties']['hygieneRating'].update({'nullable': True})
    new_api_component_details_dto_v2['properties']['integrityRating'].update({'nullable': True})
    new_api_component_details_dto_v2['properties']['relativePopularity'].update({'nullable': True})

    json_spec['components']['schemas']['ApiComponentDetailsDTOV2'] = new_api_component_details_dto_v2

# Fix `ApiComponentEvaluationResultDTOV2` schema
if 'components' in json_spec and 'schemas' in json_spec['components'] \
        and 'ApiComponentEvaluationResultDTOV2' in json_spec['components']['schemas']:
    print('Fixing schema: ApiComponentEvaluationResultDTOV2...')
    new_api_cer_dto = json_spec['components']['schemas']['ApiComponentEvaluationResultDTOV2']

    new_api_cer_dto['properties']['errorMessage'].update({'nullable': True})

    json_spec['components']['schemas']['ApiComponentEvaluationResultDTOV2'] = new_api_cer_dto

# Fix `ApiMailConfigurationDTO` schema
if 'components' in json_spec and 'schemas' in json_spec['components'] \
        and 'ApiMailConfigurationDTO' in json_spec['components']['schemas']:
    print('Fixing schema: ApiMailConfigurationDTO...')
    new_api_mail_configuration_dto = json_spec['components']['schemas']['ApiMailConfigurationDTO']

    new_api_mail_configuration_dto['properties']['password'] = {
        'type': 'string'
    }

    json_spec['components']['schemas']['ApiMailConfigurationDTO'] = new_api_mail_configuration_dto

# Fix `ApiProxyServerConfigurationDTO` schema
if 'components' in json_spec and 'schemas' in json_spec['components'] \
        and 'ApiProxyServerConfigurationDTO' in json_spec['components']['schemas']:
    print('Fixing schema: ApiProxyServerConfigurationDTO...')
    new_api_proxy_server_configuration_dto = json_spec['components']['schemas']['ApiProxyServerConfigurationDTO']

    new_api_proxy_server_configuration_dto['properties']['password'] = {
        'type': 'string'
    }

    json_spec['components']['schemas']['ApiProxyServerConfigurationDTO'] = new_api_proxy_server_configuration_dto

# Add missing schema `ApiThirdPartyScanTicketDTO`
if 'components' in json_spec and 'schemas' in json_spec['components'] \
        and 'ApiThirdPartyScanTicketDTO' not in json_spec['components']['schemas']:
    print('Adding schema: ApiThirdPartyScanTicketDTO...')

    json_spec['components']['schemas']['ApiThirdPartyScanTicketDTO'] = {
        'properties': {
            'statusUrl': {
                'type': 'string'
            }
        }
    }

# Fix Response schema for POST /api/v2/scan/applications/{applicationId}/sources/{source}
if 'paths' in json_spec and '/api/v2/scan/applications/{applicationId}/sources/{source}' in json_spec['paths']:
    if 'post' in json_spec['paths']['/api/v2/scan/applications/{applicationId}/sources/{source}']:
        print('Fixing POST /api/v2/scan/applications/{applicationId}/sources/{source}...')
        json_spec['paths']['/api/v2/scan/applications/{applicationId}/sources/{source}']['post']['responses'][
            'default']['content']['application/json'].update({
            'schema': {
                '$ref': '#/components/schemas/ApiThirdPartyScanTicketDTO'
            }
        })

# Remove APIs with incomplete schemas
API_PATHS_TO_REMOVE = {
    '/api/v2/licenseLegalMetadata/customMultiApplication/report': [],
    '/api/v2/product/license': [],
    '/api/v2/config/saml': ['put']
}
if 'paths' in json_spec:
    print('Removing paths...')
    for path, methods in API_PATHS_TO_REMOVE.items():
        print(f'   Removing: {path} : {methods}')
        if path in json_spec['paths']:
            if len(methods) == 0:
                json_spec['paths'].pop(path)
            else:
                for method in methods:
                    json_spec['paths'][path].pop(method)

# v176 Updates
# ------------------------------------------------------------------------

# Remove duplicated tags
# As of 176, some tags are added additionally with descriptions
if 'tags' in json_spec:
    print('Ensuring Tags are unique...')
    tags_seen = []
    unique_tags = []
    for tag in json_spec['tags']:
        if tag['name'] not in tags_seen:
            tags_seen.append(tag['name'])
            unique_tags.append(tag)
    json_spec['tags'] = unique_tags

# v177 Updates
# ------------------------------------------------------------------------

# Fix schema with name 'SBOM vulnerability analysis request':
SCHEMA_NAMES_TO_UPDATE = {
    'SBOM vulnerability analysis request': 'SBOMVulnerabilityAnalysisRequest'
}
for schema_to_fix in SCHEMA_NAMES_TO_UPDATE:
    print(f'Replacing Schema {schema_to_fix} with {SCHEMA_NAMES_TO_UPDATE[schema_to_fix]}', )
    schema_content = json_spec['components']['schemas'].pop(schema_to_fix, None)
    json_spec['components']['schemas'][SCHEMA_NAMES_TO_UPDATE[schema_to_fix]] = schema_content

    print(f'   Updating any paths using {schema_to_fix}...')
    ref_to_find = f'#/components/schemas/{schema_to_fix}'
    ref_to_replace_with = f'#/components/schemas/{SCHEMA_NAMES_TO_UPDATE[schema_to_fix]}'
    for path in json_spec['paths']:
        for method in json_spec['paths'][path]:
            if 'requestBody' in json_spec['paths'][path][method]:
                for content_type in json_spec['paths'][path][method]['requestBody']['content']:
                    if '$ref' in json_spec['paths'][path][method]['requestBody']['content'][content_type]['schema']:
                        if json_spec['paths'][path][method]['requestBody']['content'][content_type]['schema'][
                            '$ref'] == ref_to_find:
                            json_spec['paths'][path][method]['requestBody']['content'][content_type]['schema'][
                                '$ref'] = ref_to_replace_with

# v184 Updates
# ------------------------------------------------------------------------

# Fix Response schema for POST /api/v2/components/remediation/{ownerType}/{ownerId}
if 'paths' in json_spec and '/api/v2/components/remediation/{ownerType}/{ownerId}' in json_spec['paths']:
    if 'post' in json_spec['paths']['/api/v2/components/remediation/{ownerType}/{ownerId}']:
        print('Fixing POST /api/v2/components/remediation/{ownerType}/{ownerId}...')
        json_spec['paths']['/api/v2/components/remediation/{ownerType}/{ownerId}']['post']['responses'][
            '200'] = {
                'content': {
                    'application/json': {
                        'schema': {
                            '$ref': '#/components/schemas/ApiComponentRemediationValueDTO'
                        }
                    }
                }
            }

# Coerce `default` responses to be `200`
for path in json_spec['paths']:
    for method in json_spec['paths'][path]:
        rcs = json_spec['paths'][path][method]['responses'].keys()
        if '200' not in rcs and 'default' in rcs:
            print(f'{path} {method} needs a 200')
            json_spec['paths'][path][method]['responses']['200'] = json_spec['paths'][path][method]['responses'][
                'default']

with open('./spec/openapi.yaml', 'w') as output_yaml_specfile:
    output_yaml_specfile.write(yaml_dump(json_spec))
