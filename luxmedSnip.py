import argparse
import yaml
import coloredlogs
import json
import logging
import os
import datetime
import pushover
import shelve
import schedule
import requests
import time

from slack_sdk import WebClient

coloredlogs.install(level="INFO")
log = logging.getLogger("main")


class LuxMedSniper:
    LUXMED_LOGIN_URL = 'https://portalpacjenta.luxmed.pl/PatientPortalMobileAPI/api/token'
    NEW_PORTAL_RESERVATION_URL = 'https://portalpacjenta.luxmed.pl/PatientPortalMobileAPI/api/visits/available-terms'

    def __init__(self, configuration_file="luxmedSniper.yaml"):
        self.log = logging.getLogger("LuxMedSniper")
        self.log.info("LuxMedSniper logger initialized")
        self._loadConfiguration(configuration_file)
        self._createSession()
        self._logIn()
        pushover.init(self.config['pushover']['api_token'])
        self.pushoverClient = pushover.Client(self.config['pushover']['user_key'])
        self.slackClient = WebClient(token=self.config['slack']['api_token'])

    def _createSession(self):
        self.session = requests.session()
        self.session.headers.update({'Host': 'portalpacjenta.luxmed.pl'})
        self.session.headers.update({'Origin': "https://portalpacjenta.luxmed.pl"})
        self.session.headers.update({'Content-Type': "application/x-www-form-urlencoded"})
        self.session.headers.update({'x-api-client-identifier': 'iPhone'})
        self.session.headers.update({
            'Custom-User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, '
                                 'like Gecko) Mobile/15E148'})
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, '
                          'like Gecko) Mobile/15E148'})
        self.session.headers.update({'Accept-Language': 'pl;q=1.0, pl;q=0.9, en;q=0.8'})
        self.session.headers.update({'Accept-Encoding': 'gzip, deflate, br'})
        self.session.headers.update({'Accept': 'application/json, text/plain, */*'})

    def _loadConfiguration(self, configuration_file):
        try:
            config_data = open(
                os.path.expanduser(
                    configuration_file
                ),
                'r'
            ).read()
        except IOError:
            raise Exception('Cannot open configuration file ({file})!'.format(file=configuration_file))
        try:
            self.config = yaml.load(config_data, Loader=yaml.FullLoader)
        except Exception as yaml_error:
            raise Exception('Configuration problem: {error}'.format(error=yaml_error))

    def _logIn(self):
        login_data = {'grant_type': 'password', 'client_id': 'iPhone', 'username': self.config['luxmed']['email'],
                      'password': self.config['luxmed']['password']}
        resp = self.session.post(self.LUXMED_LOGIN_URL, login_data)
        content = json.loads(resp.text)
        self.access_token = content['access_token']
        self.refresh_token = content['refresh_token']
        self.token_type = content['token_type']
        self.session.headers.update({'Authorization': '%s %s' % (self.token_type, self.access_token)})
        self.log.info('Successfully logged in!')

    def _parseVisitsNewPortal(self, data):
        appointments = []
        content = json.loads(data)
        for term in content['AvailableVisitsTermPresentation']:
            appointments.append(
                {'AppointmentDate': '%s' % term['VisitDate']['FormattedDate'],
                 'ClinicPublicName': term['Clinic']['Name'],
                 'DoctorName': '%s' % term['Doctor']['Name']})
        return appointments

    def _getAppointmentsNewPortal(self):
        try:
            (cityId, serviceId, clinicId, doctorId) = self.config['luxmedsniper'][
                'doctor_locator_id'].strip().split('*')
        except ValueError:
            raise Exception('DoctorLocatorID seems to be in invalid format')
        data = {
            'cityId': cityId,
            'payerId': 123,
            'serviceId': serviceId,
            'languageId': 10,
            'FromDate': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            'ToDate': (datetime.datetime.now() + datetime.timedelta(
                days=self.config['luxmedsniper']['lookup_time_days'])).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'searchDatePreset': self.config['luxmedsniper']['lookup_time_days']
        }
        if clinicId != '-1':
            data['clinicId'] = clinicId
        if doctorId != '-1':
            data['doctorId'] = doctorId

        r = self.session.get(self.NEW_PORTAL_RESERVATION_URL, params=data)
        return self._parseVisitsNewPortal(r.text)

    def check(self):
        appointments = self._getAppointmentsNewPortal()
        if not appointments:
            self.log.info("No appointments found.")
            return
        for appointment in appointments:
            self.log.info(
                "Appointment found! {AppointmentDate} at {ClinicPublicName} - {DoctorName}".format(
                    **appointment))
            if not self._isAlreadyKnown(appointment):
                self._addToDatabase(appointment)
                self._sendNotification(appointment)
                self.log.info(
                    "Notification sent! {AppointmentDate} at {ClinicPublicName} - {DoctorName}".format(
                        **appointment))
            else:
                self.log.info('Notification was already sent.')

    def _addToDatabase(self, appointment):
        db = shelve.open(self.config['misc']['notifydb'])
        notifications = db.get(appointment['DoctorName'], [])
        notifications.append(appointment['AppointmentDate'])
        db[appointment['DoctorName']] = notifications
        db.close()

    def _sendNotification(self, appointment):
        try:
            if self.config['luxmedsniper']['notification_provider'] == "pushover":
                self.pushoverClient.send_message(self.config['pushover']['message_template'].format(**appointment,
                                                                                                    title=self.config[
                                                                                                        'pushover'][
                                                                                                        'title']))
            else:
                self.slackClient.chat_postMessage(channel=self.config['slack']['channel'],
                                                  text=self.config['slack']['message_template'].format(**appointment,
                                                                                                       title=
                                                                                                       self.config[
                                                                                                           'pushover'][
                                                                                                           'title']))
        except Exception as s:
            log.error(s)

    def _isAlreadyKnown(self, appointment):
        db = shelve.open(self.config['misc']['notifydb'])
        notifications = db.get(appointment['DoctorName'], [])
        db.close()
        if appointment['AppointmentDate'] in notifications:
            return True
        return False


def work(config):
    try:
        luxmedSniper = LuxMedSniper(configuration_file=config)
        luxmedSniper.check()
    except Exception as s:
        log.error(s)


if __name__ == "__main__":
    log.info("LuxMedSniper - Lux Med Appointment Sniper")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config",
        help="Configuration file path (default: luxmedSniper.yaml)", default="luxmedSniper.yaml"
    )
    parser.add_argument(
        "-d", "--delay",
        type=int, help="Delay in s of fetching updates (default: 1800)", default="1800"
    )
    args = parser.parse_args()
    work(args.config)
    schedule.every(args.delay).seconds.do(work, args.config)
    while True:
        schedule.run_pending()
        time.sleep(1)
