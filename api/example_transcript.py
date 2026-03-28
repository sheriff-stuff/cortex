"""Hardcoded example transcript for template preview rendering."""

from api.transcribe import Segment

EXAMPLE_SEGMENTS: list[Segment] = [
    Segment(start=0, end=12, speaker="Speaker 1",
            text="Alright, let's get started. Today we need to cover the product launch timeline, the marketing budget, and the new hiring plan."),
    Segment(start=14, end=28, speaker="Speaker 2",
            text="Sure. So for the product launch, we're looking at a Q3 release. The engineering team has the core features done, but we still need to finish the payment integration and the onboarding flow."),
    Segment(start=30, end=42, speaker="Speaker 1",
            text="Can we move the launch date to September instead of August? That would give us more buffer for QA."),
    Segment(start=44, end=58, speaker="Speaker 2",
            text="Yes, September works. If marketing can start the pre-launch campaign in August, we should be fine. I'll update the roadmap to reflect the September target."),
    Segment(start=62, end=78, speaker="Speaker 3",
            text="On the marketing side, do we have budget approval for the paid ads campaign? I submitted the proposal last week but haven't heard back."),
    Segment(start=80, end=95, speaker="Speaker 1",
            text="I haven't seen the approval yet either. Let's flag that as an open item. Sarah, can you follow up with finance on the budget approval by end of day tomorrow?"),
    Segment(start=98, end=112, speaker="Speaker 3",
            text="Will do. I'll send them a reminder and cc you on the email."),
    Segment(start=115, end=132, speaker="Speaker 2",
            text="For the hiring plan, we decided to go with two senior engineers and one junior. We need to post the job listings this week."),
    Segment(start=135, end=150, speaker="Speaker 1",
            text="Agreed. Let's use the new job board we signed up for. Mike, can you draft the job descriptions by Thursday?"),
    Segment(start=152, end=168, speaker="Speaker 2",
            text="Sure, I'll have them ready by Thursday. Should we also reach out to that recruiting agency we used last time?"),
    Segment(start=170, end=182, speaker="Speaker 1",
            text="Good idea. Let's hold off on the agency for now and see how the job board performs first. We can revisit in two weeks."),
    Segment(start=185, end=198, speaker="Speaker 3",
            text="One more thing — are we still planning the team offsite for April? I need to start booking the venue if so."),
    Segment(start=200, end=215, speaker="Speaker 1",
            text="Yes, the offsite is confirmed for April fifteenth. Go ahead and book the venue. Let's keep it under five thousand dollars."),
    Segment(start=218, end=230, speaker="Speaker 1",
            text="Alright, good meeting everyone. To recap: September launch, hiring posts this week, and Sarah follows up on the budget. Let's reconvene next Tuesday."),
]
