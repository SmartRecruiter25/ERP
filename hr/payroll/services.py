from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from hr.employees.models import Employee, EmployeeStatus
from hr.org_structure.models import Company

from hr.attendance.models import AttendanceRecord, AttendanceStatus, EmployeeShiftAssignment
from hr.contracts.models import EmployeeContract, ContractStatus 
from hr.payroll.models import PayrollRun, PayrollRunStatus, PayrollItem

from hr.ess.models import LeaveRequest, LeaveStatus, LeaveType, OvertimeRequest, ApprovalStatus  


WEEKLY_HOLIDAYS = {4}  
OVERTIME_MULTIPLIER = Decimal("1.50")  


def q2(x: Decimal) -> Decimal:
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def daterange(d1: date, d2: date):
    cur = d1
    while cur <= d2:
        yield cur
        cur += timedelta(days=1)


def is_weekly_holiday(day: date) -> bool:
    return day.weekday() in WEEKLY_HOLIDAYS


def get_company_from_user(user) -> Company | None:
    employee_profile = getattr(user, "employee_profile", None)
    if employee_profile is not None:
        return employee_profile.company
    return Company.objects.first()


def get_employee_shift_for_date(employee: Employee, day: date):
    return (
        EmployeeShiftAssignment.objects
        .filter(employee=employee, start_date__lte=day, end_date__gte=day)
        .order_by("-is_primary", "-start_date")
        .first()
    )


def expected_daily_hours(employee: Employee, day: date) -> Decimal:
    assign = get_employee_shift_for_date(employee, day)
    if assign and assign.shift:
        return Decimal(str(assign.shift.required_daily_hours))
    return Decimal("8.00")


def get_active_contract(employee: Employee, day: date) -> EmployeeContract | None:
    return (
        EmployeeContract.objects
        .filter(
            employee=employee,
            status=ContractStatus.ACTIVE,
            start_date__lte=day,
            end_date__gte=day,
        )
        .order_by("-start_date")
        .first()
    )


def approved_leaves_map(employee: Employee, start: date, end: date) -> dict[date, dict]:
    
    qs = LeaveRequest.objects.filter(
        employee=employee,
        status=LeaveStatus.APPROVED,
        start_date__lte=end,
        end_date__gte=start,
    )

    m: dict[date, dict] = {}
    for lr in qs:
        cur = lr.start_date
        while cur <= lr.end_date:
            if start <= cur <= end:
                m[cur] = {"type": lr.leave_type, "half": bool(lr.is_half_day)}
            cur += timedelta(days=1)
    return m


def approved_overtime_hours(employee: Employee, start: date, end: date) -> Decimal:
    qs = OvertimeRequest.objects.filter(
        employee=employee,
        status=ApprovalStatus.APPROVED,
        date__range=[start, end],
    )
    total = Decimal("0.00")
    for r in qs:
        total += Decimal(str(r.hours or 0))
    return q2(total)


@dataclass
class PayrollCalcResult:
    ok: bool
    currency: str
    basic_salary: Decimal
    allowances: Decimal
    overtime_pay: Decimal
    deductions: Decimal
    breakdown: dict
    error: str | None = None


def calc_employee_payroll_for_run(employee: Employee, run: PayrollRun) -> PayrollCalcResult:
    start = run.period_start
    end = run.period_end

  
    contract = get_active_contract(employee, start) or get_active_contract(employee, end)
    if not contract:
        return PayrollCalcResult(
            ok=False,
            currency="USD",
            basic_salary=Decimal("0.00"),
            allowances=Decimal("0.00"),
            overtime_pay=Decimal("0.00"),
            deductions=Decimal("0.00"),
            breakdown={"error": "No active contract in period"},
            error="No active contract",
        )

    basic_salary = q2(Decimal(str(contract.base_salary)))
    currency = getattr(contract, "currency", "USD") or "USD"

 
    att_qs = AttendanceRecord.objects.filter(employee=employee, date__range=[start, end])
    att_by_day = {a.date: a for a in att_qs}

  
    leave_by_day = approved_leaves_map(employee, start, end)

   
    expected_hours = Decimal("0.00")
    expected_work_days = 0

    worked_hours = Decimal("0.00")
    late_minutes = 0
    early_minutes = 0

    absent_hours = Decimal("0.00")
    unpaid_leave_hours = Decimal("0.00")

    for day in daterange(start, end):
        if is_weekly_holiday(day):
            continue

        expected_work_days += 1
        day_expected = expected_daily_hours(employee, day)
        expected_hours += day_expected

        rec = att_by_day.get(day)
        if rec:
            worked_hours += Decimal(str(rec.total_hours or 0))
            late_minutes += int(rec.late_minutes or 0)
            early_minutes += int(rec.early_leave_minutes or 0)

        leave_info = leave_by_day.get(day)
        if leave_info:
           
            if leave_info["type"] == LeaveType.UNPAID:
                hours = (day_expected / Decimal("2")) if leave_info["half"] else day_expected
                unpaid_leave_hours += hours
            
            continue

       
        if not rec:
            absent_hours += day_expected
        else:
         
            if rec.status == AttendanceStatus.ABSENT:
                absent_hours += day_expected

    expected_hours = q2(expected_hours)
    worked_hours = q2(worked_hours)
    absent_hours = q2(absent_hours)
    unpaid_leave_hours = q2(unpaid_leave_hours)

    
    denom = expected_hours if expected_hours > 0 else Decimal("1.00")
    hourly_rate = (basic_salary / denom).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

   
    late_hours = q2(Decimal(late_minutes) / Decimal("60"))
    early_hours = q2(Decimal(early_minutes) / Decimal("60"))

    late_deduction = q2(late_hours * hourly_rate)
    early_deduction = q2(early_hours * hourly_rate)

    
    absent_deduction = q2(absent_hours * hourly_rate)
    unpaid_leave_deduction = q2(unpaid_leave_hours * hourly_rate)

   
    ot_hours = approved_overtime_hours(employee, start, end)

    
    if ot_hours == 0:
      
        ot_hours = q2(sum((Decimal(str(a.overtime_hours or 0)) for a in att_qs), Decimal("0.00")))

    overtime_pay = q2(ot_hours * hourly_rate * OVERTIME_MULTIPLIER)

  
    allowances = Decimal("0.00")

    deductions = q2(late_deduction + early_deduction + absent_deduction + unpaid_leave_deduction)

    breakdown = {
        "employee_id": employee.id,
        "employee_code": employee.employee_code,
        "contract_id": contract.id,

        "period_start": str(start),
        "period_end": str(end),

        "expected_work_days": expected_work_days,
        "expected_hours": str(expected_hours),
        "hourly_rate": str(hourly_rate),

        "worked_hours": str(worked_hours),

        "late_minutes": late_minutes,
        "early_leave_minutes": early_minutes,
        "late_deduction": str(late_deduction),
        "early_deduction": str(early_deduction),

        "absent_hours": str(absent_hours),
        "absent_deduction": str(absent_deduction),

        "unpaid_leave_hours": str(unpaid_leave_hours),
        "unpaid_leave_deduction": str(unpaid_leave_deduction),

        "overtime_hours_used": str(ot_hours),
        "overtime_multiplier": str(OVERTIME_MULTIPLIER),
        "overtime_pay": str(overtime_pay),

        "allowances": str(allowances),
        "total_deductions": str(deductions),
        "net_salary": str(q2(basic_salary + allowances + overtime_pay - deductions)),
    }

    return PayrollCalcResult(
        ok=True,
        currency=currency,
        basic_salary=basic_salary,
        allowances=allowances,
        overtime_pay=overtime_pay,
        deductions=deductions,
        breakdown=breakdown,
    )


def ensure_monthly_run(company: Company, year: int, month: int) -> PayrollRun:
    
    last_day = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)
    end = date(year, month, last_day)

    run, _ = PayrollRun.objects.get_or_create(
        company=company,
        year=year,
        month=month,
        defaults={
            "name": f"{calendar.month_name[month]} {year} Payroll",
            "period_start": start,
            "period_end": end,
            "status": PayrollRunStatus.DRAFT,
        },
    )
    return run


@transaction.atomic
def generate_payroll_items(run: PayrollRun, employees_qs=None) -> dict:
    
    if run.status != PayrollRunStatus.DRAFT:
        raise ValidationError("لا يمكن توليد الرواتب إلا عندما تكون PayrollRun بحالة Draft.")

    if employees_qs is None:
        employees_qs = Employee.objects.filter(company=run.company, status=EmployeeStatus.ACTIVE)

    generated = 0
    skipped = 0
    errors = []

    for emp in employees_qs:
        res = calc_employee_payroll_for_run(emp, run)
        if not res.ok:
            skipped += 1
            errors.append({"employee_id": emp.id, "employee_code": emp.employee_code, "error": res.error})
            continue

        PayrollItem.objects.update_or_create(
            payroll_run=run,
            employee=emp,
            defaults={
                "basic_salary": res.basic_salary,
                "allowances": res.allowances,
                "overtime_pay": res.overtime_pay,
                "deductions": res.deductions,
                "currency": res.currency,
                "breakdown": res.breakdown,
            }
        )
        generated += 1

    run.recalculate_totals()

    return {
        "success": True,
        "run_id": run.id,
        "company": run.company.name,
        "year": run.year,
        "month": run.month,
        "generated": generated,
        "skipped": skipped,
        "errors_preview": errors[:20],
    }