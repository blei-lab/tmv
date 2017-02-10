from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(SnowballingSession)
admin.site.register(Query)
admin.site.register(Doc)
admin.site.register(WoSArticle)
