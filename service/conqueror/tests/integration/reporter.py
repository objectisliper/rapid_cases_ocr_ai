import base64
import csv
import datetime
import json
import os
import pathlib
import time

from service.conqueror.managers import process_request

# from fuzzywuzzy import fuzz

# Таким образом JSON типичного запроса будет выглядеть примерно так
# {
# SearchPhraseIdentifiers:["error", "exception"],
# URLContains:["wpadmin", "wordpress.com"], //тут будет полный массив со ВСЕХ рулов
# TextContains:["MySQL", "MariaDB"], //тут будет полный массив со ВСЕХ рулов
# VideoBody: "sfasfadfa23dflskf;l….sdfasf"
# }
#
#
# Ответ на такой запрос должен быть примерно такой
# {
# SearchPhrasesFound:["Contact validation error: Last name is missing.",
# "Mysql error: username and password are not correct"],
# URLContainsResults:["wpadmin"=true, "wordpress.com"=false], //найдено было каждое слово в урле или нет
# TextContainsResults:["MySQL"=true, "MariaDB"=false], // найдено было каждое слово в урле или нет
# }

class ReportGenerator():
    report = []

    def __clean_report(self):
        self.report = [["Video", "Phrases Found", "URL Contains", "Text Contains", "Total score", "Duration", "Response JSON"]]

    def __calc_TrueFalse_score(self, expected_dict, real_dict):
        sum = 0.0
        for key in expected_dict:
            if key in real_dict:
                if real_dict[key] == expected_dict[key]:
                    sum += 1

        result = sum / len(expected_dict)

        # convert to percents
        result = result * 100

        return result

    def __calc_test_score(self, expected_response, real_response):
        score = {
            "SearchPhrasesFound": 0,
            "URLContainsResults": 0,
            "TextContainsResults": 0,
            "Total": 0
        }

        # calculate SearchPhrasesFound score
        sum = 0.0
        if len(expected_response["SearchPhrasesFound"]) > 0:
            for key in expected_response["SearchPhrasesFound"]:
                if key in real_response["SearchPhrasesFound"]:
                    sum += 1
            score["SearchPhrasesFound"] = sum / len(expected_response["SearchPhrasesFound"])
            # convert to percents
            score["SearchPhrasesFound"] = score["SearchPhrasesFound"] * 100

        score["URLContainsResults"] = self.__calc_TrueFalse_score(expected_response["URLContainsResults"],
                                                                  real_response["URLContainsResults"])
        score["TextContainsResults"] = self.__calc_TrueFalse_score(expected_response["TextContainsResults"],
                                                                   real_response["TextContainsResults"])

        score["Total"] = (score["SearchPhrasesFound"]
                          + score["URLContainsResults"]
                          + score["TextContainsResults"]
                          ) / 3

        return score

    def __process_videotest(self, test_folder_path):
        input_json = os.path.join(test_folder_path, 'input.json')
        expected_json = os.path.join(test_folder_path, 'expected.json')
        with open(input_json) as json_file:
            request = json.load(json_file)

        with open(expected_json) as json_file:
            expected_result = json.load(json_file)

        # read video
        video_filenames = [name for name in os.listdir(test_folder_path)
                          if str.endswith(name.lower(), '.webm')]

        if len(video_filenames) > 0:
            video_filename = video_filenames[0]
            video_path = os.path.join(test_folder_path, video_filename)
            with open(video_path, 'rb') as video:
                request['VideoBody'] = base64.b64encode(video.read()).decode('utf-8')

        json_encoded_request = json.dumps(request)
        start_time = time.time()
        response = process_request(json_encoded_request)
        end_time = time.time()

        test_duration = end_time - start_time
        score = self.__calc_test_score(expected_result, response)

        return response, test_duration, score

    def test_process_request___folder(self, config_path):
        test_folders = os.listdir(config_path)
        self.__clean_report()
        total_duration = 0.0

        for test_folder in test_folders:
            test_folder_path = os.path.join(config_path, test_folder)
            if os.path.isfile(test_folder_path):
                continue
            test_result, duration, score = self.__process_videotest(test_folder_path)
            total_duration += duration
            row = [test_folder, score["SearchPhrasesFound"], score["URLContainsResults"], score["TextContainsResults"], score["Total"], duration, test_result]
            self.report.append(row)
            print(row)

        print(f'Total time in seconds: {total_duration}')

    def save_report(self, config_path):
        time_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        report_filename = os.path.join(config_path, "report" + time_suffix + ".csv")
        print ('Saving report to file: ' + report_filename)
        with open(report_filename, "w", newline='') as file:
            writer = csv.writer(file, delimiter='\t')
            writer.writerows(self.report)
        print('Report was sucessfully saved!')


if __name__ == "__main__":
    test_root_folder = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / 'different_site_errors').as_posix()
    rp = ReportGenerator()
    rp.test_process_request___folder(test_root_folder)
    rp.save_report(test_root_folder)