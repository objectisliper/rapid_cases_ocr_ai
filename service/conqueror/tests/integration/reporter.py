import base64
import csv
import datetime
import json
import os
import pathlib
import time

from numpy import mean

from service.conqueror.managers import process_request

from fuzzywuzzy import fuzz

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
            for expected_phrase in expected_response["SearchPhrasesFound"]:
                # if expected_phrase in real_response["SearchPhrasesFound"]:
                #     sum += 1
                for real_phrase in real_response["SearchPhrasesFound"]:
                    if expected_phrase in real_phrase or fuzz.partial_ratio(real_phrase, expected_phrase) > 80:
                        sum += 1
                        break
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
        problem_folders = []

        for test_folder in test_folders:
            test_folder_path = os.path.join(config_path, test_folder)
            if os.path.isfile(test_folder_path):
                continue

            print("processing folder: " + test_folder)
            try:
                test_result, duration, score = self.__process_videotest(test_folder_path)
                total_duration += duration
                row = [test_folder, score["SearchPhrasesFound"], score["URLContainsResults"], score["TextContainsResults"], score["Total"], duration, test_result]
                self.report.append(row)
                print(row)
            except Exception as e:
                problem_folders.append(test_folder)
                print('Some problem with processing folder "' + test_folder + '"')
                print('Exception: {0}'.format(e))

        avg_phrases_found = mean([row[1] for row in self.report[1:]])
        avg_URL_contains = mean([row[2] for row in self.report[1:]])
        avg_Text_contains = mean([row[3] for row in self.report[1:]])
        avg_total_score = mean([row[4] for row in self.report[1:]])
        avg_time = mean([row[5] for row in self.report[1:]])

        self.report.append([])
        #self.report.append(['-------------------------','------------------','------------------','------------------','------------------','------------------','------------------'])
        self.report.append(['Average', avg_phrases_found, avg_URL_contains, avg_Text_contains, avg_total_score, avg_time])
        self.report.append([])
        self.report.append(['Total score', avg_total_score])
        self.report.append(['Total time', str(datetime.timedelta(seconds=total_duration))])

        if len(problem_folders) > 0:
            print('\nProblem folders: ')
            for folder in problem_folders:
                print(folder)

        print('--------------------------------------------------')
        print('Total score: ' + str(avg_total_score))
        print('Average time: ' + str(avg_time))
        print('Total time: ' + str(datetime.timedelta(seconds=total_duration)))

    def save_report(self, config_path):
        time_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(config_path, "report" + time_suffix + ".csv")
        print ('Saving report to file: ' + report_filename)
        with open(report_filename, "w", newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerows(self.report)
        print('Report was sucessfully saved!')


if __name__ == "__main__":
    test_root_folder = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / 'different_site_errors').as_posix()
    rp = ReportGenerator()
    rp.test_process_request___folder(test_root_folder)
    rp.save_report(test_root_folder)