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
    phrase_similarity = 80

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
                    if expected_phrase in real_phrase or \
                            (
                                len(expected_phrase) <= int(round(len(real_phrase)*1.33, 0))
                                and fuzz.partial_ratio(real_phrase, expected_phrase) > self.phrase_similarity
                            ):
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

    def process_videotest(self, test_folder_path, recognition_settings={}):
        input_json = os.path.join(test_folder_path, 'input.json')
        expected_json = os.path.join(test_folder_path, 'expected.json')
        with open(input_json) as json_file:
            request = json.load(json_file)
        if "caseClasificationRules" in request.keys():
            request["TextContains"] = request["caseClasificationRules"]["page"]
            request["URLContains"] = request["caseClasificationRules"]["url"]
            request.pop("caseClasificationRules", None)
            request["SearchPhraseIdentifiers"] = request["searchPhraseIdentifiers"]
            request.pop("searchPhraseIdentifiers", None)


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
        response = process_request(json_encoded_request, recognition_settings)
        end_time = time.time()

        test_duration = end_time - start_time
        if "comparing_similarity_for_phrases" in recognition_settings:
            default_phrase_similarity = self.phrase_similarity
            self.phrase_similarity = recognition_settings["comparing_similarity_for_phrases"]
            score = self.__calc_test_score(expected_result, response)
            self.phrase_similarity = default_phrase_similarity
        else:
            score = self.__calc_test_score(expected_result, response)

        return response, test_duration, score

    def test_process_request___folder(self, config_path, recognition_settings={}):
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
                test_result, duration, score = self.process_videotest(test_folder_path, recognition_settings)
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

        return avg_total_score, avg_time

    def save_report(self, config_path, filename_suffix=""):
        time_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        additional_suffix = "_" + filename_suffix if len(filename_suffix) > 0 else ""

        report_filename = os.path.join(config_path, "report" + time_suffix + additional_suffix + ".csv")
        if len(report_filename) > 250:
            filename_without_suffix = os.path.join(config_path, "report" + time_suffix + ".csv")
            report_filename = os.path.join(config_path, "report" + time_suffix + additional_suffix[0:(250-len(filename_without_suffix))] + ".csv")

        print ('Saving report to file: ' + report_filename)
        with open(report_filename, "w", newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerows(self.report)
        print('Report was sucessfully saved!')

    def save_many_configuration_report(self, config_path, results: dict):
        time_suffix = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        report_filename = os.path.join(config_path, "report_" + time_suffix + "___many_configurations.csv")

        list_for_saving = [["Configuration", "Total score", "Average time", "Optimum"]]
        for configuration in results.keys():
            list_for_saving.append(results[configuration])

        print ('Saving report to file: ' + report_filename)
        with open(report_filename, "w", newline='', encoding='utf-8') as file:
            writer = csv.writer(file, delimiter=';')
            writer.writerows(list_for_saving)
        print('Report was sucessfully saved!')






def get_report_suffix(recognition_settings):
    suffix = ""
    if len(recognition_settings.keys()) > 0:
        for key in recognition_settings.keys():
            suffix += "___" + str(key) + "." + str(recognition_settings[key])

    return suffix.lstrip('_')

if __name__ == "__main__":
    test_root_folder = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / 'different_site_errors').as_posix()
    # test_root_folder = (pathlib.Path(__file__).parent.parent / 'integration_tests_video' / 'live').as_posix()
    test_settings = {}
    # test_settings["skip_frames"] = [10, 15, 20, 25, 30 , 35, 40, 45, 50, 60, 70, 80, 90, 100, 125, 150, 200, 300]
    # test_settings["skip_frames"] = [20, 30, 50]
    # test_settings["use_gray_colors"] = [False, True]
    # test_settings["invert_colors"] = [False, True]
    # test_settings["use_morphology"] = [False, True]
    # test_settings["use_threshold_with_gausian_blur"] = [False, True]
    # test_settings["use_adaptiveThreshold"] = [False, True]
    # test_settings["max_y_position_for_URL"] = [80, 90, 100, 110, 120]
    # test_settings["word_min_confidence"] = [-1, 0, 50, 80, 90, 95]
    test_settings["comparing_similarity_for_phrases"] = [50, 80, 90]

    fullgrid = True

    test_confugurations = []
    if fullgrid:
        import itertools
        allNames = sorted(test_settings)
        list_of_test_configurations = list(itertools.product(*(test_settings[Name] for Name in allNames)))
        for configuration_values in list_of_test_configurations:
            configuration = {}
            for index, key in enumerate(allNames):
                configuration[key] = configuration_values[index]

            test_confugurations.append(configuration)
    else:
        test_confugurations = [{setting: value}
                               for setting in test_settings.keys()
                               for value in test_settings[setting]]

    rp = ReportGenerator()

    # single video test
    # rp.process_videotest((pathlib.Path(__file__).parent.parent / 'integration_tests_video' / 'live' / 'ZjZO877mtGfcpprep-sLDKAhC-sYb84A').as_posix())

    if len(test_confugurations) < 1:
        rp.test_process_request___folder(test_root_folder)
        rp.save_report(test_root_folder)
    else:
        results = {}
        best_score = 0
        best_time = 99999999999999
        optimum_score = 0
        optimum_total_score = 0
        optimum_time = 9999999999999
        best_score_parameters = ""
        best_time_parameters = ""
        optimum_parameters = ""

        for configuration in test_confugurations:
            report_suffix = get_report_suffix(configuration)
            total_score, avg_time = rp.test_process_request___folder(test_root_folder, configuration)
            if total_score > best_score:
                best_score = total_score
                best_score_parameters = report_suffix

            if avg_time < best_time:
                best_time = avg_time
                best_time_parameters = report_suffix

            score = total_score + (100 - avg_time*avg_time)
            if score > optimum_score:
                optimum_score = score
                optimum_total_score = total_score
                optimum_time = avg_time
                optimum_parameters = report_suffix

            results[report_suffix] = [report_suffix, total_score, avg_time, score]
            rp.save_report(test_root_folder, report_suffix)

        print("Best score: " + str(best_score) + "           Parameters: " + best_score_parameters)
        print("Best avg time: " + str(best_time) + "           Parameters: " + best_time_parameters)
        print("Optimum: score = " + str(optimum_total_score) + "          time = " + str(optimum_time) + "           Parameters: " + optimum_parameters)
        rp.save_many_configuration_report(test_root_folder, results)