import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from src.config import settings


@pytest.fixture(scope="module")
def driver():
    options = Options()
    if settings.SELENIUM_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")

    # In environments where chromedriver is installed or managed
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except Exception:
        # Fallback to local PATH webdriver
        driver = webdriver.Chrome(options=options)

    driver.implicitly_wait(10)
    yield driver
    driver.quit()


@pytest.mark.selenium
def test_dashboard_title_and_elements_rendered(driver):
    """
    Validates that the benchmark portal renders main titles, input fields, and action buttons.
    """
    driver.get(settings.SELENIUM_BASE_URL)
    wait = WebDriverWait(driver, 10)

    # Check title
    title_elem = wait.until(EC.presence_of_element_located((By.ID, "app-title")))
    assert "LLM Benchmark Portal" in title_elem.text

    # Check key interactive elements exist
    assert driver.find_element(By.ID, "username-input").is_displayed()
    assert driver.find_element(By.ID, "password-input").is_displayed()
    assert driver.find_element(By.ID, "login-btn").is_displayed()
    assert driver.find_element(By.ID, "run-benchmark-btn").is_displayed()
    assert driver.find_element(By.ID, "send-query-btn").is_displayed()


@pytest.mark.selenium
def test_login_flow_and_role_badge_update(driver):
    """
    Validates the authentication flow: entering credentials and asserting the role badge updates.
    """
    driver.get(settings.SELENIUM_BASE_URL)
    wait = WebDriverWait(driver, 10)

    username_input = driver.find_element(By.ID, "username-input")
    password_input = driver.find_element(By.ID, "password-input")
    login_btn = driver.find_element(By.ID, "login-btn")

    username_input.clear()
    username_input.send_keys("benchmark@example.com")
    password_input.clear()
    password_input.send_keys("BenchPass123!")
    login_btn.click()

    # Wait for role badge to update to benchmark_admin
    wait.until(EC.text_to_be_present_in_element((By.ID, "current-role"), "benchmark_admin"))
    role_text = driver.find_element(By.ID, "current-role").text
    assert "benchmark_admin" in role_text
