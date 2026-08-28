"""Test CRUD operations."""
import pytest
from sqlalchemy.orm import Session
from fastapi import status
import models, schemas, crud
from database import Base, engine, SessionLocal


def test_profile_crud(db_session: Session):
    """Test profile CRUD operations."""
    # Create profile (using get_or_create_profile)
    profile = crud.get_or_create_profile(db_session, user_id=1)
    assert profile.id is not None

    # Update profile with test data
    update_data = schemas.UserProfileBase(
        age=30,
        height=180.5,
        current_weight=75.0,
        target_weight=70.0,
        goal="cut",
        target_physique="Fit",
        experience_months=12,
        focus_muscle_group="Chest",
        activity_level="moderate",
        dietary_notes="No pork",
        schedule_notes="Morning workouts",
        injury_notes="None",
        daily_calorie_target=2000,
        daily_protein_target=150,
        daily_carb_target=200,
        daily_fat_target=60,
        onboarding_completed=True
    )
    updated = crud.update_profile(db_session, update_data.model_dump(exclude_unset=True), user_id=1)
    assert updated.id is not None
    assert updated.age == 30
    assert updated.goal == "cut"
    assert updated.onboarding_completed == True

    # Get profile
    retrieved = crud.get_or_create_profile(db_session, user_id=1)
    assert retrieved.id == updated.id
    assert retrieved.age == 30

    # Update profile again
    update_data2 = schemas.UserProfileBase(
        goal="bulk",
        target_weight=80.0
    )
    updated2 = crud.update_profile(db_session, update_data2.model_dump(exclude_unset=True), user_id=1)
    assert updated2.goal == "bulk"
    assert updated2.target_weight == 80.0
    assert updated2.age == 30  # Unchanged

    # Verify update persisted
    retrieved_after = crud.get_or_create_profile(db_session, user_id=1)
    assert retrieved_after.goal == "bulk"
    assert retrieved_after.target_weight == 80.0


def test_nutrition_log_crud(db_session: Session):
    """Test nutrition log CRUD operations."""
    # Create nutrition log
    nutrition_data = schemas.NutritionLogCreate(
        meal_name="Test Meal",
        ingredients="Test ingredients",
        calories=500,
        protein=30,
        carbs=50,
        fats=20,
        time_target="12:00"
    )

    nutrition_log = crud.create_nutrition_log(db_session, nutrition_data, user_id=1)
    assert nutrition_log.id is not None
    assert nutrition_log.meal_name == "Test Meal"
    assert nutrition_log.calories == 500

    # Get nutrition logs for today
    from datetime import date
    today_logs = crud.get_nutrition_logs_by_date(db_session, date.today(), user_id=1)
    assert len(today_logs) == 1
    assert today_logs[0].id == nutrition_log.id

    # Clear nutrition logs for today
    deleted_count = crud.clear_nutrition_logs_by_date(db_session, date.today(), user_id=1)
    assert deleted_count == 1

    # Verify cleared
    today_logs_after = crud.get_nutrition_logs_by_date(db_session, date.today(), user_id=1)
    assert len(today_logs_after) == 0


def test_workout_program_crud(db_session: Session):
    """Test workout program CRUD operations."""
    # Create workout program
    program_data = schemas.WorkoutProgramCreate(
        day_name="Monday - Chest",
        is_active=True,
        exercises=[
            schemas.ExerciseCreate(
                name="Bench Press",
                target_sets=4,
                target_reps="8-12",
                muscle_group="Chest",
                target_rpe=8.0,
                exercise_type="primary_compound",
                stretch_mediated=False,
                unilateral=False,
                equipment="barbell",
                technique_cue="Keep feet flat on ground",
                progression_model="double_progression"
            ),
            schemas.ExerciseCreate(
                name="Incline Dumbbell Press",
                target_sets=3,
                target_reps="10-15",
                muscle_group="Chest",
                target_rpe=8.0,
                exercise_type="secondary_compound",
                stretch_mediated=True,
                unilateral=True,
                equipment="dumbbell",
                technique_cue="Focus on upper chest",
                progression_model="double_progression"
            )
        ]
    )

    program = crud.create_workout_program(db_session, program_data, user_id=1)
    assert program.id is not None
    assert program.day_name == "Monday - Chest"
    assert len(program.exercises) == 2

    # Get workout programs
    programs = crud.get_workout_programs(db_session, user_id=1)
    assert len(programs) == 1
    assert programs[0].id == program.id

    # Clear workout programs
    crud.clear_workout_programs(db_session, user_id=1)
    programs_after = crud.get_workout_programs(db_session, user_id=1)
    assert len(programs_after) == 0


def test_body_metric_crud(db_session: Session):
    """Test body metric CRUD operations."""
    # Create body metric
    metric_data = schemas.BodyMetricCreate(
        weight=75.5,
        waist=85.0,
        chest=100.0,
        arm=35.0,
        sleep_hours=7.5,
        note="Felt good"
    )

    body_metric = crud.create_body_metric(db_session, metric_data, user_id=1)
    assert body_metric.id is not None
    assert body_metric.weight == 75.5
    assert body_metric.waist == 85.0
    assert body_metric.sleep_hours == 7.5

    # Get body metrics
    metrics = crud.get_body_metrics(db_session, days=7, user_id=1)
    assert len(metrics) == 1
    assert metrics[0].id == body_metric.id

    # Verify weight updated in profile
    profile = crud.get_or_create_profile(db_session, user_id=1)
    assert profile.current_weight == 75.5


def test_memory_crud(db_session: Session):
    """Test memory CRUD operations."""
    # Create memory
    memory = crud.create_memory(
        db_session,
        category="preference",
        content="User prefers chicken over fish",
        importance=8,
        keywords="chicken,fish,preference",
        memory_key="diet.chicken_preference",
        user_id=1
    )
    assert memory.id is not None
    assert memory.category == "preference"
    assert memory.importance == 8
    assert memory.content == "User prefers chicken over fish"

    # Get memories
    memories = crud.get_all_memories(db_session, user_id=1)
    assert len(memories) >= 1

    # Get recent memories
    recent_memories = crud.get_recent_memories(db_session, user_id=1)
    assert len(recent_memories) >= 1

    # Search memories
    searched = crud.search_memories(db_session, "chicken", user_id=1)
    assert len(searched) >= 1
    assert searched[0].content == "User prefers chicken over fish"

    # Update memory
    updated = crud.update_memory(
        db_session,
        memory_id=memory.id,
        content="User prefers both chicken and fish",
        importance=9
    )
    assert updated.content == "User prefers both chicken and fish"
    assert updated.importance == 9

    # Forget memory
    forgotten = crud.forget_memory(db_session, "chicken preference", user_id=1)
    assert forgotten is not None
    assert "chicken" in forgotten.content.lower()

    # Verify forgotten
    memories_after = crud.get_all_memories(db_session, user_id=1)
    # Should not contain the forgotten memory (might still have others)
    chicken_memories = [m for m in memories_after if "chicken" in m.content.lower()]
    assert len(chicken_memories) == 0


def test_meal_plan_crud(db_session: Session):
    """Test meal plan CRUD operations."""
    # Create meal plan items
    meal_items = [
        schemas.MealPlanItemCreate(
            meal_name="Breakfast",
            time_target="08:00",
            description="Oatmeal with fruits",
            calories=400,
            protein=20,
            carbs=50,
            fats=15
        ),
        schemas.MealPlanItemCreate(
            meal_name="Lunch",
            time_target="13:00",
            description="Grilled chicken salad",
            calories=500,
            protein=40,
            carbs=30,
            fats=20
        )
    ]

    # Replace meal plan
    replaced_items = crud.replace_meal_plan(db_session, meal_items, user_id=1)
    assert len(replaced_items) == 2
    assert replaced_items[0].meal_name == "Breakfast"
    assert replaced_items[1].meal_name == "Lunch"

    # Get meal plan
    meal_plan = crud.get_meal_plan(db_session, user_id=1)
    assert len(meal_plan) == 2
    assert meal_plan[0].meal_name == "Breakfast"

    # Clear meal plan
    crud.clear_meal_plan(db_session, user_id=1)
    meal_plan_after = crud.get_meal_plan(db_session, user_id=1)
    assert len(meal_plan_after) == 0


def test_chat_message_crud(db_session: Session):
    """Test chat message CRUD operations."""
    # Save chat message
    message = crud.save_chat_message(
        db_session,
        role="user",
        content="Hello Jarvis",
        intent="chat",
        session_id="test_session",
        user_id=1
    )
    assert message.id is not None
    assert message.role == "user"
    assert message.content == "Hello Jarvis"
    assert message.session_id == "test_session"

    # Get chat history
    history = crud.get_chat_history(db_session, session_id="test_session", user_id=1)
    assert len(history) >= 1
    assert history[0].content == "Hello Jarvis"
    assert history[0].role == "user"

    # Clear chat history
    deleted_count = crud.clear_chat_history(db_session, session_id="test_session", user_id=1)
    assert deleted_count >= 1

    # Verify cleared
    history_after = crud.get_chat_history(db_session, session_id="test_session", user_id=1)
    assert len(history_after) == 0


def test_daily_checkin_crud(db_session: Session):
    """Test daily check-in CRUD operations."""
    # Upsert daily check-in
    checkin_data = {
        "mood": 4,
        "energy": 5,
        "sleep_quality": 4,
        "soreness": 2,
        "notes": "Felt energetic today"
    }

    checkin = crud.upsert_daily_checkin(db_session, checkin_data, user_id=1)
    assert checkin.id is not None
    assert checkin.mood == 4
    assert checkin.energy == 5
    # Note: readiness_score is calculated in jarvis_brain.process_checkin, not in CRUD layer
    # In actual usage, it's passed in the data dictionary

    # Get today's check-in
    today_checkin = crud.get_today_checkin(db_session, user_id=1)
    assert today_checkin is not None
    assert today_checkin.id == checkin.id

    # Get check-in history
    history = crud.get_checkin_history(db_session, days=7)
    assert len(history) >= 1