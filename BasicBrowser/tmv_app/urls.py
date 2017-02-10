from django.conf.urls import url, include
from django.conf import settings
from django.conf.urls.static import static

from tmv_app.views import index, topic_detail, term_detail, doc_detail, topic_list_detail, topic_presence_detail, stats, settings, apply_settings, topic_random, doc_random, term_random, institution_detail, author_detail, runs, apply_run_filter, delete_run, update_run, get_docs

from django.contrib.auth.decorators import login_required

app_name = 'tmv_app'

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^topic/(?P<topic_id>\d+)/$', login_required(topic_detail), name="topic_detail"),
    url(r'^term/(?P<term_id>\d+)/$', login_required(term_detail), name="term_detail"),
    url(r'^doc/(?P<doc_id>.+)/$', login_required(doc_detail)),
    url(r'^author/(?P<author_name>.+)/$', login_required(author_detail)),
    url(r'^institution/(?P<institution_name>.+)/$', login_required(institution_detail)),
    url(r'^topic_list$', login_required(topic_list_detail)),
    url(r'^topic_presence$', login_required(topic_presence_detail)),
    url(r'^stats$', login_required(stats)),
    url(r'^settings$', login_required(settings)),
    url(r'^settings/apply$', login_required(apply_settings)),
    url(r'^runs$', login_required(runs), name='runs'),
    url(r'^update/(?P<run_id>\d+)$', login_required(update_run), name='update'),
    url(r'^runs/apply/(?P<new_run_id>\d+)$', login_required(apply_run_filter)),
    url(r'^runs/delete/(?P<new_run_id>\d+)$', login_required(delete_run)),
    url(r'^topic/random$', login_required(topic_random)),
    url(r'^doc/random$', login_required(doc_random)),
    url(r'^term/random$', login_required(term_random)),
    url(r'^get_docs$', login_required(get_docs), name="get_docs")]
    # Example:
    # (r'^BasicBrowser/', include('BasicBrowser.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),



#onyl serve static content for development
#urlpatterns += static(settings.STATIC_URL,document_root='static')

