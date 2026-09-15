from datetime import date, timedelta
from odoo.tests.common import TransactionCase
from odoo import fields

class TestMuqeemOperations(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls.env['hr.employee'].create({'name':'Muqeem Workflow Test','company_id':cls.env.company.id})
        cls.profile = cls.env['muqeem.workforce.profile'].create({
            'employee_id': cls.employee.id, 'nationality_id': cls.env.ref('base.sa').id,
            'iqama_number':'240000123','iqama_issue_date':date.today()-timedelta(days=300),
            'iqama_expiry':date.today()+timedelta(days=25),'passport_number':'P1234567',
            'passport_expiry':date.today()+timedelta(days=180),'visa_expiry':date.today()+timedelta(days=45),
            'work_permit_expiry':date.today()+timedelta(days=90),'insurance_expiry':date.today()+timedelta(days=120),
            'sponsor_id':'700000001','sponsor_name':'Test Sponsor','muqeem_status':'active'})

    def test_risk_engine(self):
        self.profile.action_refresh_operational_state()
        self.assertIn(self.profile.risk_level, ('medium','high','critical'))
        self.assertLessEqual(self.profile.travel_readiness, 100)

    def test_service_gates_and_submission(self):
        req=self.env['muqeem.service.request'].create({'profile_id':self.profile.id,'service_code':'iqama_renew'})
        req.action_start(); req.action_precheck()
        self.assertIn(req.state, ('documents','query'))
        if req.state=='documents':
            req.document_gate='pass'
            req.action_validate_documents(); req.action_approve()
            if req.state=='payment': req.action_register_payment()
            req.action_submit()
            self.assertEqual(req.state,'submitted')
            req.action_process()
            self.assertEqual(req.state,'done')

    def test_travel_risk_detects_late_return(self):
        permit=self.env['muqeem.travel.permit'].create({'profile_id':self.profile.id,'permit_type':'single_exit_reentry','travel_date':date.today(),'expected_return':date.today()+timedelta(days=30),'return_before':date.today()+timedelta(days=15)})
        self.assertEqual(permit.travel_risk,'red')

    def test_sponsor_transfer_workflow(self):
        transfer=self.env['muqeem.sponsor.transfer'].create({'profile_id':self.profile.id,'current_sponsor_id':'700000001','current_sponsor_name':'Old','new_sponsor_id':'700000002','new_sponsor_name':'New','reason':'Business'})
        transfer.action_check(); self.assertEqual(transfer.state,'approval'); transfer.action_approve(); transfer.action_submit(); transfer.action_accept(); transfer.action_complete()
        self.assertEqual(self.profile.sponsor_id,'700000002')
