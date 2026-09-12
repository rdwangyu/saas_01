from django.test import TestCase
from django.urls import reverse

from .models import (CASE_LIMIT_PER_COMPANY, PROJECT_LIMIT_PER_COMPANY,
                     STAGE_LIMIT_PER_PROJECT, Case, Company, ProjectProgress,
                     ProjectStage, Staff)


class QuotaTestCase(TestCase):
    """公司级配额：案例 20 / 项目 20；单个项目阶段 12。"""

    def setUp(self):
        self.company = Company.objects.create(name="白云装饰", credit_code="91330000AAAA")
        self.staff = Staff.objects.create(name="张三", phone="13800000000", company=self.company)
        self.staff.set_password("secret123")
        self.staff.save(update_fields=["password"])
        session = self.client.session
        session["staff_id"] = self.staff.pk
        session.save()

    def _fill_cases(self, count):
        for i in range(count):
            Case.objects.create(company=self.company, title=f"案例{i}")

    def _fill_projects(self, count):
        for i in range(count):
            ProjectProgress.objects.create(
                company=self.company, project_name=f"项目{i}", address="某地", project_no=f"NO{i}"
            )

    def test_case_create_blocked_at_limit(self):
        self._fill_cases(CASE_LIMIT_PER_COMPANY)
        resp = self.client.post(reverse("dashboard:case_create"), {"title": "第21个"})
        self.assertEqual(resp.status_code, 200)  # 校验失败，回显表单
        self.assertContains(resp, f"每个公司最多创建 {CASE_LIMIT_PER_COMPANY} 个案例")
        self.assertFalse(Case.objects.filter(title="第21个").exists())

    def test_case_create_allowed_below_limit(self):
        self._fill_cases(CASE_LIMIT_PER_COMPANY - 1)
        resp = self.client.post(reverse("dashboard:case_create"), {"title": "最后一个"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Case.objects.filter(title="最后一个").exists())

    def test_soft_deleted_case_frees_quota(self):
        self._fill_cases(CASE_LIMIT_PER_COMPANY)
        Case.objects.filter(company=self.company).first().delete()  # 软删除
        resp = self.client.post(reverse("dashboard:case_create"), {"title": "补一个"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Case.objects.filter(title="补一个").exists())

    def test_project_create_blocked_at_limit(self):
        self._fill_projects(PROJECT_LIMIT_PER_COMPANY)
        resp = self.client.post(
            reverse("dashboard:project_create"),
            {"project_no": "NO-NEW", "project_name": "第21个", "address": "某地"},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"每个公司最多创建 {PROJECT_LIMIT_PER_COMPANY} 个项目")
        self.assertFalse(ProjectProgress.objects.filter(project_no="NO-NEW").exists())

    def test_quota_is_per_company(self):
        self._fill_cases(CASE_LIMIT_PER_COMPANY)
        other = Company.objects.create(name="其他公司", credit_code="91330000BBBB")
        other_staff = Staff.objects.create(name="李四", phone="13900000000", company=other)
        session = self.client.session
        session["staff_id"] = other_staff.pk
        session.save()
        resp = self.client.post(reverse("dashboard:case_create"), {"title": "别家的案例"})
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Case.objects.filter(title="别家的案例", company=other).exists())

    def test_stage_create_blocked_at_limit(self):
        project = ProjectProgress.objects.create(
            company=self.company, project_name="项目", address="某地", project_no="NO1"
        )
        for i in range(STAGE_LIMIT_PER_PROJECT):
            ProjectStage.objects.create(project=project, name=f"阶段{i}")
        resp = self.client.post(
            reverse("dashboard:stage_create", kwargs={"pk": project.pk}), {"name": "第13个"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f"每个项目最多 {STAGE_LIMIT_PER_PROJECT} 个阶段")
        self.assertFalse(project.stages.filter(name="第13个").exists())

    def test_soft_deleted_stage_frees_quota(self):
        project = ProjectProgress.objects.create(
            company=self.company, project_name="项目", address="某地", project_no="NO1"
        )
        for i in range(STAGE_LIMIT_PER_PROJECT):
            ProjectStage.objects.create(project=project, name=f"阶段{i}")
        project.stages.first().delete()  # 软删除
        resp = self.client.post(
            reverse("dashboard:stage_create", kwargs={"pk": project.pk}), {"name": "补充阶段"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(project.stages.filter(name="补充阶段").exists())

    def test_stage_limit_is_per_project(self):
        p1 = ProjectProgress.objects.create(
            company=self.company, project_name="项目1", address="某地", project_no="NO1"
        )
        for i in range(STAGE_LIMIT_PER_PROJECT):
            ProjectStage.objects.create(project=p1, name=f"阶段{i}")
        p2 = ProjectProgress.objects.create(
            company=self.company, project_name="项目2", address="某地", project_no="NO2"
        )
        resp = self.client.post(
            reverse("dashboard:stage_create", kwargs={"pk": p2.pk}), {"name": "新项目的阶段"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(p2.stages.filter(name="新项目的阶段").exists())

    def test_editing_existing_record_is_not_blocked(self):
        self._fill_cases(CASE_LIMIT_PER_COMPANY)
        case = Case.objects.filter(company=self.company).first()
        resp = self.client.post(
            reverse("dashboard:case_update", kwargs={"pk": case.pk}), {"title": "改个名字"}
        )
        self.assertEqual(resp.status_code, 302)
        case.refresh_from_db()
        self.assertEqual(case.title, "改个名字")

    def test_list_page_hides_create_button_at_limit(self):
        self._fill_cases(CASE_LIMIT_PER_COMPANY - 1)
        url = reverse("dashboard:case_list")
        create_url = reverse("dashboard:case_create")
        resp = self.client.get(url)
        self.assertContains(resp, f"案例 {CASE_LIMIT_PER_COMPANY - 1}/{CASE_LIMIT_PER_COMPANY}")
        self.assertContains(resp, create_url)

        self._fill_cases(1)  # 刚好到上限
        resp = self.client.get(url)
        self.assertContains(resp, f"案例 {CASE_LIMIT_PER_COMPANY}/{CASE_LIMIT_PER_COMPANY}")
        self.assertContains(resp, "btn disabled")
        self.assertNotContains(resp, f'href="{create_url}"')

    def test_stage_quota_shown_on_project_detail(self):
        project = ProjectProgress.objects.create(
            company=self.company, project_name="项目", address="某地", project_no="NO1"
        )
        url = reverse("dashboard:project_detail", kwargs={"pk": project.pk})
        create_url = reverse("dashboard:stage_create", kwargs={"pk": project.pk})
        resp = self.client.get(url)
        self.assertContains(resp, f"0/{STAGE_LIMIT_PER_PROJECT}")
        self.assertContains(resp, create_url)

        for i in range(STAGE_LIMIT_PER_PROJECT):
            ProjectStage.objects.create(project=project, name=f"阶段{i}")
        resp = self.client.get(url)
        self.assertContains(resp, f"{STAGE_LIMIT_PER_PROJECT}/{STAGE_LIMIT_PER_PROJECT}")
        self.assertContains(resp, "btn sm disabled")
        self.assertNotContains(resp, f'href="{create_url}"')

    def test_superuser_admin_not_limited(self):
        """超管后台不受配额限制：配额只做在 dashboard 表单上。"""
        self._fill_cases(CASE_LIMIT_PER_COMPANY)
        extra = Case(company=self.company, title="超管加的案例")
        extra.full_clean()  # 不应抛出 ValidationError
        extra.save()
        self.assertTrue(Case.objects.filter(title="超管加的案例").exists())
