from django.db import models
class Course(models.Model):
    class Category(models.TextChoices):
        EE = 'ee', 'EE module'
        CS = 'cs', 'CS module'
        SEMINAR = 'seminar', 'Seminar'
        LAB = 'lab', 'Lab'
        NON_TECH = 'non-tech', 'Non-tech'
        BASIC = 'basic', 'Basic'
    class Difficulty(models.TextChoices):
        HARD = 'hard', 'Hard'
        MEDIUM = 'medium', 'Medium'
        SIMPLE = 'simple', 'Simple'
    class ExamForm(models.TextChoices):
        OPEN = 'open', 'Open Book'
        CLOSED = 'closed', 'Close Book'
        REPORT = 'report', 'Just Representation/Report'
        ORAL = 'oral', 'Oral Exam'
    class Semester(models.TextChoices):
        WINTER = 'winter', 'Winter semester'
        SUMMER = 'summer', 'Summer semester'
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=8, choices=Category.choices)
    difficulty = models.CharField('Exam difficulty', max_length=6, choices=Difficulty.choices)
    exam_form = models.CharField(max_length=6, choices=ExamForm.choices)
    description = models.TextField(max_length=5000)
    semester = models.CharField(max_length=6, choices=Semester.choices)
    capacity_limited = models.BooleanField('Capacity limited', default=False)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ['name', 'pk']
    def __str__(self):
        return self.name


class UsefulLink(models.Model):
    name = models.CharField('Website name', max_length=200)
    url = models.URLField('Website URL', max_length=2000)
    description = models.TextField('Description', max_length=5000)
    class Meta:
        ordering = ['pk']
    def __str__(self):
        return self.name

class Tip(models.Model):
    title = models.CharField('Title', max_length=200)
    body = models.TextField('Body', max_length=10000)
    class Meta:
        ordering = ['pk']
    def __str__(self):
        return self.title
