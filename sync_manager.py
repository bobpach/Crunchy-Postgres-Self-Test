""" Synchronizes the target ArgoCD application
"""
from logging_manager import LoggingManager
import urllib3
import requests
import os


class SyncManager:
    """ Synchronizes the target ArgoCD application
    """

    # init the logging manager
    lm = LoggingManager()

    def synch_argocd_application(self):
        """ Uses ArgoCD API to synch teh target application
        """
        # gets the argocd token
        token = os.getenv("ARGOCD_TOKEN")

        # assigns the token to the set
        # strips trailing "\n" that is added when the
        # token is added to the set
        cookies = {'argocd.token': token.strip("\n")}
        LoggingManager.logger.debug(cookies)

        ip = os.getenv("ARGOCD_SERVICE_ADDRESS")
        app_name = os.getenv("ARGOCD_APP_NAME").lower()

        # creates the url that will be used in the synch api call
        synch_url = 'https://%s/api/v1/applications/%s/sync' % (ip, app_name)
        LoggingManager.logger.debug("synch_url: %s" % (synch_url))

        # suppresses the warning that gets generated when using
        # self-signed certs in the argocd deployment
        verify_tls = os.getenv("ARGOCD_VERIFY_TLS").lower()
        if verify_tls == "true":
            verify = True
        else:
            verify = False
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # post the synch request to the argocd api
        try:
            resp = requests.post(synch_url, cookies=cookies, verify=verify)
            LoggingManager.logger.info("Successfully synched the %s ArgoCD "
                                       "application." % (app_name))
        except (Exception) as error:
            LoggingManager.logger.error(error, exc_info=True)

        # log response values
        LoggingManager.logger.debug(resp)
        LoggingManager.logger.debug(resp.content)
