"""F1 데이터 정제·검증 파이프라인.

- extra_data: 추가 데이터 5종 압축 해제 (python -m pipeline.extra_data, run_web.bat이 자동 실행)
- recovery: 오염 6종 진단·복구·격리 (python -m pipeline.recovery)
- validate_cleaned: 정제 결과 + 추가 5종 검증 VC01~VC71 (python -m pipeline.validate_cleaned)
- dictionary_pdf: 표준사전 PDF 생성 (python -m pipeline.dictionary_pdf)
"""
