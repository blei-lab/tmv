from django.http import HttpResponse
from django.template import loader
from django.apps import apps
from django.conf import settings
from django.conf import settings
from django.utils.module_loading import import_module

def index(request):
    template = loader.get_template('scoping/base_index.html')
    apps = [
        {'name': 'scoping','app_url':'/scoping'},
        {'name': 'tmv_app','app_url':'/tmv_app/topic_presence'}
    ]
    context = {
        'site_header': 'MCC-APSIS',
        'app_list': apps
    }
    return HttpResponse(template.render(context, request))

