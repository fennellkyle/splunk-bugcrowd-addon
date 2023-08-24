

# encoding = utf-8

import json
import os
import sys
import time
import datetime

'''
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
'''
'''
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
'''

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # api_key = definition.parameters.get('api_key', None)
    pass

def collect_events(helper, ew):
    """Implement your data collection logic here"""

    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    opt_api_key = helper.get_arg('api_key')

    helper.set_log_level("info")
    
    return_limit = 100
    return_offset = 0
    more_submissions = True
    
    while more_submissions:
        url = "https://api.bugcrowd.com/submissions"
        # note: offset has max of <10000. verify the max_hits is not more than that.
        param = {
            'fields[submission]': 'title,duplicate,custom_fields,submitted_at,bug_url,vrt_id,severity,state,last_transitioned_to_not_applicable_at,last_transitioned_to_not_reproducible_at,last_transitioned_to_out_of_scope_at,last_transitioned_to_informational_at,last_transitioned_to_triaged_at,last_transitioned_to_unresolved_at,last_transitioned_to_resolved_at,assignee,researcher,description,activities,program,target,monetary_rewards',
            'include': 'monetary_rewards,researcher,assignee,program,target',
            'fields[program]': 'name',
            'fields[target]': 'name',
            'page[limit]': return_limit,
            'page[offset]': return_offset,
            'filter[state]': 'unresolved,resolved,informational,new,triaged'}
        head = {'Authorization': 'Token ' + opt_api_key, 'Accept': 'application/vnd.bugcrowd+json'}
        final_result = []

        response = helper.send_http_request(url, 'GET', parameters=param, payload=None,
                                        headers=head, cookies=None, verify=True, cert=None,
                                        timeout=None, use_proxy=True)

        if response.status_code == 200:
            r_json = response.json()
        else:
            helper.log_error("Bugcrowd API request failed with a status code of: %s" % response.status_code)
            return
        
        if r_json['meta']['count'] < return_limit:
            more_submissions = False
        else:
            return_offset = return_offset + return_limit

        for submission in r_json['data']:
            
            # Using the submission id with number of activities as the checkpoint. There seems to be no better way to track changes to a submission.
            # In future versions of the API there will be better ways to handle this.
            sub_id = submission['id']
            num_of_activities = str(submission['relationships']['activities']['links']['related']['meta']['total_hits'])
            check_point = "{}-{}".format(sub_id, num_of_activities)

            state = helper.get_check_point(check_point)
            
            if state is None:
                # remove unnecessary 'links' 
                submission['relationships']['assignee'].pop('links')
                submission['relationships']['researcher'].pop('links')
                submission['relationships']['program'].pop('links')
                submission['relationships']['target'].pop('links')
                submission['relationships']['monetary_rewards'].pop('links')
                submission.pop('links')
                
                final_result.append(submission)
                helper.save_check_point(check_point, "Indexed")
            #helper.delete_check_point(latest_activity)
    
        for included in r_json['included']:
            state = helper.get_check_point(included['id'])
            if state is None:
                # remove unnecessary 'links' and 'relationships'
                included.pop('links')
                if 'relationships' in included:
                    included.pop('relationships')
                final_result.append(included)
                helper.save_check_point(included['id'], "Indexed")
            #helper.delete_check_point(included['id'])

        # To create a splunk event
        event = helper.new_event(json.dumps(final_result), host='api.bugcrowd.com', index=helper.get_output_index(), source=helper.get_input_type(), sourcetype=helper.get_sourcetype(), done=True, unbroken=True)
        ew.write_event(event)
        helper.log_info("Indexed %s submissions" % r_json['meta']['count'])
    
    helper.log_info("Successfully retrieved and indexed all new/updated Bugcrowd submissions.")

