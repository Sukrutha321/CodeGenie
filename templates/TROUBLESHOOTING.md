# Troubleshooting Signup Issues

## Common Problems and Solutions

### Problem 1: Signup Returns Error
**Symptoms**: User fills out signup form, clicks "Create Account", gets error message

**Solutions**:

1. **Check Password Length**
   - Password must be at least 8 characters
   - Make sure you're not using spaces at the start/end

2. **Check Email Format**
   - Must contain @ and .
   - Example: user@example.com

3. **Check if Email Already Exists**
   - Try a different email address
   - Each email can only be registered once

### Problem 2: Nothing Happens When Clicking Signup
**Cause**: JavaScript error or Flask not running

**Solutions**:

1. **Check Flask is Running**
   ```bash
   python app.py
   ```
   Should see: `Running on http://127.0.0.1:5000`

2. **Check Browser Console**
   - Press F12 to open Developer Tools
   - Click "Console" tab
   - Look for error messages in red

3. **Check Network Tab**
   - F12 → Network tab
   - Try signup again
   - Look for `/api/signup` request
   - Check if it's showing red (error)

### Problem 3: "An error occurred during registration"
**Cause**: Server-side error

**Solutions**:

1. **Check Flask Terminal Output**
   - Look for error messages in the terminal where Flask is running
   - Should see detailed error logs

2. **Run Test Script**
   ```bash
   # In separate terminal (while Flask is running)
   python test_api.py
   ```
   This will test the API endpoints directly

### Problem 4: Signup Works but Can't Login
**Cause**: User data not saved or login credentials don't match

**Solutions**:

1. **Check Flask Terminal**
   - After successful signup, you should see:
   ```
   Signup successful - Email: your@email.com, Name: Your Name
   ```

2. **Try Exact Same Email/Password**
   - Email is case-sensitive
   - Password is case-sensitive
   - No extra spaces

3. **Restart Flask**
   - User data is stored in memory
   - Restarting Flask clears all registered users
   - You'll need to signup again

## Testing Signup Manually

### Using Browser:
1. Open `http://localhost:5000`
2. Click "Create Account" tab
3. Fill in:
   - Full Name: Test User
   - Email: test@example.com
   - Password: TestPass123
   - Confirm: TestPass123
4. Click "Create Account"
5. Should see: "Account created successfully!"
6. Switch to "Sign In" tab
7. Use same email/password to login

### Using Test Script:
```bash
# Start Flask in one terminal
python app.py

# In another terminal
python test_api.py
```

Expected output:
```
✓ PASS: Signup
✓ PASS: Login
✓ PASS: Duplicate Email
✓ PASS: Short Password

Total: 4/4 tests passed
🎉 All tests passed!
```

## Debugging Steps

1. **Enable Debug Mode**
   The app.py file now has logging enabled. Check terminal output for:
   ```
   DEBUG - Signup attempt - Email: user@example.com
   INFO - Signup successful
   ```

2. **Check Request Data**
   In browser console (F12), before error appears:
   ```javascript
   // Check what's being sent
   console.log('Sending:', {name, email, password});
   ```

3. **Check Response**
   In Network tab (F12), click the `/api/signup` request:
   - Check "Response" tab for error message
   - Check "Headers" tab for status code

## Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "All fields are required" | Empty field | Fill in all fields |
| "Please enter a valid email" | Missing @ or . | Use proper email format |
| "Password must be at least 8 characters" | Short password | Use longer password |
| "Email already registered" | Duplicate email | Use different email or login instead |
| "An error occurred during registration" | Server error | Check Flask terminal logs |

## Still Having Issues?

1. **Copy Full Error Message**
   - From browser console (F12)
   - From Flask terminal
   
2. **Check File Structure**
   ```
   codegenie/
   ├── templates/
   │   ├── login.html    ← Must be here
   │   └── homepage.html ← Must be here
   ├── app.py
   └── requirements.txt
   ```

3. **Verify Dependencies Installed**
   ```bash
   pip list | grep Flask
   ```
   Should show:
   - Flask
   - Flask-CORS

4. **Try Demo Account**
   Instead of creating new account, try logging in with:
   - Email: demo@codegenie.dev
   - Password: Demo2024!

## Advanced Debugging

### Check if Flask is receiving requests:
Add this to `app.py` before any route:
```python
@app.before_request
def log_request():
    logger.debug(f"Request: {request.method} {request.path}")
```

### Test API with curl:
```bash
curl -X POST http://localhost:5000/api/signup \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","email":"test@test.com","password":"Test1234"}'
```

Should return:
```json
{"success":true,"message":"Account created successfully"}
```
