from b08_model_core.knowledge.paper_candidates import paper_candidates
from b08_model_core.knowledge.patent_candidates import patent_candidates


def test_knowledge_outputs_are_first_class_deliverables():
    assert len(patent_candidates()) >= 3
    assert len(paper_candidates()) >= 3
    assert any("阶段" in c.title for c in patent_candidates())
