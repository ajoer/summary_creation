import nltk.data
import pandas as pd
import sys
from collections import Counter
from statistics import stdev
from tabulate import tabulate


"""
	Review the data from MTurk experiments to approve and reject summary creations. 

	Input: csv file from MTurk results page
	Output: csv file with approve/reject for each task/worker. This can be directly uploaded to MTurk for approval/rejection.

	Checks the following:

	Demographics:
	1) check for each worker whether they have filled in the demographic information at least once.
	2) check for each worker whether there are any discrepancies in the demographic information.
	3) check whether the age inputs correspond

	Task:
	4) check for each worker for each task whether the summary fulfills the requirements.

"""

class ReviewAssignments():

	def __init__(self, data):
		self.data = data
		self.demographics_dict = {}
		self.justification = """ As mentioned in the instructions, this is grounds for rejection: 'You can complete as many summary rating tasks as you want. You will be paid for the number of tasks you complete. If you leave a question unanswered, the task is incomplete,	and you will not be paid for that task. Afterwards, we will ask you four questions about who you are. If there are discrepancies in your answers to the demographic questions, we will exclude you from the experiment, and you will not be paid.'
		"""

		self.total_assignments = self.data.shape[0]
		self.rejected_assignments = 0
		self.approved_column = []
		self.rejected_column = []
		self.rejections = [["Reason for rejection", "Worker", "Person", "Task duration"]]
		self._get_minimum_worktime()
		self._make_demographics_dict()
		self.sent_detector = nltk.data.load('tokenizers/punkt/english.pickle')

	def _demographics_complete(self, worker_data):
		# Verify whether each demographic element has an answer, i.e. one True value per element options.
		
		demographic_columns = {
			"age": ['Answer.age.30', 'Answer.age.older', 'Answer.age.younger'], #, 
			"gender": ['Answer.gender.female', 'Answer.gender.male', 'Answer.gender.other'],
			"race": ['Answer.race.american_indian','Answer.race.asian', 'Answer.race.black', 
				'Answer.race.hispanic', 'Answer.race.other', 'Answer.race.white']
		}

		for demographic_element in demographic_columns:
			if not True in [worker_data[column] for column in demographic_columns[demographic_element]]:
				reason = f"missing {demographic_element}"
				return False, reason
		
		if not worker_data["Answer.typed_age"]:
			reason = "missing typed age"
			return False, reason

		return True, ""
		
	def _get_worker_demographics(self, worker_data): # race_division = binary or all
		# Make worker demographics dictionary
		demographics = {
			"age": None,
			"agegroup": None,
			"gender": None,
			"race": None
		}
		
		# Age
		demographics["age"] = worker_data['Answer.typed_age']

		if worker_data[f'Answer.age.older']:
			demographics["agegroup"] = "older than 30"
		elif worker_data[f'Answer.age.younger']:
			demographics["agegroup"] = "younger than 30"
		elif worker_data[f'Answer.age.30']:
			demographics["agegroup"] = "30"

		# Gender
		for gender in ['female', 'male', 'other']:
			if worker_data[f'Answer.gender.{gender}']:
				demographics["gender"] = gender

		# Race
		for race in ['white', 'black', 'asian', 'american_indian','hispanic', 'other']:
			if worker_data[f'Answer.race.{race}']:
				demographics["race"] = race
		return demographics

	def _make_demographics_dict(self):
		for index, worker_data in self.data.iterrows():

			demographics = self._get_worker_demographics(worker_data)
			if None in demographics.values(): continue
			self.demographics_dict[worker_data["WorkerId"]] = demographics	

	def _verify_demographics(self, worker_id): #data):
		# Verify that the demographics are complete and have no discrepancies. 
		# Return True (verified) or False (rejected).
		# Reject worker if incomplete demographics
		# complete, reason = self._demographics_complete(worker_data)
		# if not complete:
			
		if worker_id not in self.demographics_dict.keys(): 
			print("Worker not in demographics dict:\t", worker_id)
			return False, f"Incomplete demographics."

		verified = True
		reason = ""

		# Reject worker if discrepancies in age:
		age = self.demographics_dict[worker_id]["age"]
		if age == 3030: age = 30
		agegroup = self.demographics_dict[worker_id]["agegroup"]

		if ( age > 30 and agegroup != "older than 30" or
			 age < 30 and agegroup != "younger than 30" or
			 age == 30 and agegroup != "30" ):
			reason = f"Discrepancies in age. You put that you are {agegroup}, but typed that you are {age}."
			verified = False

		return verified, reason

	def _verify_task_completion(self, worker_data):
		# Verify that the summary fulfills the requirements (2-5 sentences, != biography)
		# TODO: re-write to fit summary creation task
		biography = worker_data["Input.biography"]
		summary = []
		for number in range(1,5): # should be range(1,5)
			sentence = worker_data[f'Answer.sentence_{number}']
			if sentence != sentence: continue # filter out nan values
			summary.append(sentence)
		
		if summary == biography:
			reason = f"Your summary is the same as the biography."
			return False, reason
		
		if len(summary) >= len(biography):
			reason = f"Your summary is not shorter than the biography."
			return False, reason

		string_summary = ". ".join(summary)
		number_of_sentences = len(self.sent_detector.tokenize(string_summary.strip()))
		
		# if number_of_sentences < 2:
		# 	if len(summary) == 0: quantity = "sentences"
		# 	if len(summary) == 1: quantity = "sentence"
		# 	reason = f"Your summary is too short ({number_of_sentences} {quantity}). The minimum requirement is 2 sentences."
		# 	return False, reason

		# if number_of_sentences > 5:
		# 	reason = f"Your summary is too long ({number_of_sentences} sentences). The maximum requirement is 5 sentences."
		# 	return False, reason

		return True, "", summary

	def _get_minimum_worktime(self):
		# Get average normalized worktime, and standard deviation. 
		# Used to exclude workers who spend too little time on task.
		self.normalized_worktimes = {}
		
		for index, worker_data in self.data.iterrows():
			time = worker_data["WorkTimeInSeconds"]
			read_words = len(worker_data["Input.biography"].split())
			produced_words = 0
			for num in range(1,5):
				sentence = worker_data[f"Answer.sentence_{num}"]
				if sentence != sentence: continue
				produced_words += len(sentence.split())
			normalized_worktime = time/(read_words+produced_words)
			self.normalized_worktimes[f"{worker_data['WorkerId']}_{index}"] = normalized_worktime

		average = sum(self.normalized_worktimes.values())/len(self.normalized_worktimes)
		standard_deviation = stdev(list(self.normalized_worktimes.values()))
		self.minimum_worktime = average-standard_deviation

	def _do_rejection(self, reason, worker_id, task_id, worktime, assignment_status):
		if assignment_status == "Submitted":
			self.rejections.append([reason, worker_id, task_id, worktime])
			self.rejected_assignments += 1
		self.rejected_column.append(reason+self.justification)
		self.approved_column.append("")

	def main(self):
		# Review and approve/reject assignments based on time spent on assignment and complete demographics.
		for index, worker_data in self.data.iterrows():

			if worker_data["AssignmentStatus"] != "Submitted":
				self.rejected_column.append(worker_data["Reject"])
				self.approved_column.append(worker_data["Approve"])
				continue

			worker_id = worker_data["WorkerId"]
			person = worker_data["Input.person"]
			worktime = worker_data["WorkTimeInSeconds"]

			# Too short time spent
			if self.normalized_worktimes[f"{worker_id}_{index}"] < self.minimum_worktime:
				reason = f"You spent an unreasonably short amount of time on the task ({worktime} seconds) compared to other workers and the length of the texts."
				self._do_rejection(reason, worker_id, person, worktime, worker_data["AssignmentStatus"])

			else:
				# Reject based on demographics
				verification, reason = self._verify_demographics(worker_id)
				if not verification:
					self._do_rejection(reason, worker_id, person, worktime, worker_data["AssignmentStatus"])
					
				# Reject based on task incompletion
				else:
					verification, reason, summary = self._verify_task_completion(worker_data)
					if not verification:
						self._do_rejection(reason, worker_id, person, worktime, worker_data["AssignmentStatus"])
					else:
						# Approve the rest
						reason = ""
						self.rejected_column.append("")
						self.approved_column.append("x")

						# Manually check the texts of these:
						print(worker_data["HITId"])
						print(summary)
						print()


		self.data["Approve"] = self.approved_column
		self.data["Reject"] = self.rejected_column
		self.data.to_csv(f"data/mturk/output/reviewed/{sys.argv[1]}.csv", index=False)

		print()
		print(tabulate(self.rejections))
		print(f"Number of rejected assignments:\t{self.rejected_assignments} ({self.rejected_assignments/self.total_assignments})")
		print()
		print("NB: watch out for the rejected assignments due to time. Double check those!")

if __name__ == "__main__":
	data = pd.read_csv(f"data/mturk/output/raw/{sys.argv[1]}.csv", sep=",")
	ReviewAssignments(data).main()