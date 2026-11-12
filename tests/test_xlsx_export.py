"""Bộ 5 file Excel: đủ file, đủ nội dung, có ảnh xem nhanh."""
import io
import zipfile

import openpyxl

from conftest import fill_project


def _png():
    from PIL import Image
    bio = io.BytesIO()
    Image.new("RGB", (300, 200), (200, 80, 40)).save(bio, "PNG")
    return bio.getvalue()


def test_xlsx_pack_has_five_readable_files(api):
    project = fill_project(api, api.project())
    r = api.post(f"/projects/{project['id']}/sources", data={"expected_revision": project["revision"]},
                 files={"file": ("mau-logo.png", _png(), "image/png")})
    assert r.status_code in (200, 201), r.text
    r = api.get(f"/projects/{project['id']}/package?format=xlsx")
    assert r.status_code == 200, r.text
    z = zipfile.ZipFile(io.BytesIO(r.content))
    assert sorted(z.namelist()) == ["01_TONG_QUAN_DON.xlsx", "02_YEU_CAU_CHI_TIET.xlsx", "03_CANH_VA_BAN_GIAO.xlsx",
                                    "04_TU_LIEU_KHACH_GUI.xlsx", "05_VIEC_CAN_HOI_LAI.xlsx"]
    books = {n: openpyxl.load_workbook(io.BytesIO(z.read(n))) for n in z.namelist()}
    over = books["01_TONG_QUAN_DON.xlsx"]["Tổng quan"]
    texts = [str(c.value) for row in over.iter_rows() for c in row if c.value is not None]
    assert any("QA DEMO ONLY" in t for t in texts)
    detail = books["02_YEU_CAU_CHI_TIET.xlsx"]["Yêu cầu"]
    assert detail.max_row > 15
    mat = books["04_TU_LIEU_KHACH_GUI.xlsx"]["Tư liệu"]
    assert mat["B5"].value == "mau-logo.png" and mat["C5"].value == "Ảnh"
    assert len(mat._images) == 1
    assert "Cần hỏi lại" in books["05_VIEC_CAN_HOI_LAI.xlsx"].sheetnames
