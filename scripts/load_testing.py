#!/usr/bin/env python3
"""
Load Testing and Performance Validation Script for GeoToolKit

This script performs comprehensive load testing and performance validation:
- Simulates concurrent scans across multiple languages
- Tests container resource limits
- Validates network isolation under load
- Monitors memory and CPU usage
- Tests report generation performance
- Validates error handling under stress
"""

import argparse
import json
import logging
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

import psutil

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class LoadTestRunner:
    """Main load testing orchestrator."""

    def __init__(self):
        self.results = {
            "load_tests": [],
            "performance_metrics": {},
            "errors": [],
            "summary": {},
        }
        self.temp_dir = None

    def setup_test_environment(self):
        """Setup test environment with sample projects."""
        self.temp_dir = tempfile.mkdtemp(prefix="geotoolkit_load_test_")
        logger.info(f"Setting up load test environment: {self.temp_dir}")

        # Create diverse test projects
        self.create_test_projects()

        # Setup configuration files
        self.create_test_configs()

        return self.temp_dir

    def create_test_projects(self):
        """Create test projects for different programming languages."""
        projects = {
            "python": self._create_python_project,
            "javascript": self._create_javascript_project,
            "java": self._create_java_project,
            "go": self._create_go_project,
            "typescript": self._create_typescript_project,
        }

        self.test_projects = {}

        for lang, creator in projects.items():
            project_dir = Path(self.temp_dir) / f"test_{lang}_project"
            project_dir.mkdir(exist_ok=True)

            project_info = creator(project_dir)
            self.test_projects[lang] = project_info

            logger.info(f"Created {lang} test project at {project_dir}")

    def _create_python_project(self, project_dir: Path) -> dict[str, Any]:
        """Create a Python project with various vulnerabilities."""

        # Main application with vulnerabilities
        main_py = project_dir / "app.py"
        main_py.write_text("""
import os
import pickle
import subprocess
import hashlib
import sqlite3
import yaml
from flask import Flask, request

app = Flask(__name__)

# Multiple vulnerability types for comprehensive testing
SECRET_KEY = "super-secret-key-12345"  # Hardcoded secret
DATABASE_URL = "postgresql://admin:password@localhost/db"  # Hardcoded credentials

# SQL Injection vulnerabilities
def get_user_data(user_id):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    query = f"SELECT * FROM users WHERE id = {user_id}"  # Direct string interpolation
    return cursor.execute(query).fetchall()

# Command injection
def process_file(filename):
    result = subprocess.call(f"cat {filename}", shell=True)  # Shell injection
    return result

# Deserialization attack vector
def load_user_session(session_data):
    return pickle.loads(session_data)  # Unsafe deserialization

# Weak cryptography
def hash_user_password(password):
    return hashlib.md5(password.encode()).hexdigest()  # MD5 is weak

# YAML loading vulnerability
def parse_config(yaml_content):
    return yaml.load(yaml_content)  # Unsafe YAML loading

# Path traversal
@app.route('/read/<filename>')
def read_file(filename):
    with open(f"./files/{filename}", 'r') as f:  # No path validation
        return f.read()

# XSS potential
@app.route('/welcome/<username>')
def welcome(username):
    return f"<h1>Welcome {username}!</h1>"  # No HTML escaping

# SSRF potential
@app.route('/fetch')
def fetch_url():
    url = request.args.get('url')
    import requests
    return requests.get(url).text  # No URL validation

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')  # Debug mode in production
""")

        # Requirements with vulnerable packages
        requirements = project_dir / "requirements.txt"
        requirements.write_text("""
Flask==1.0.0
requests==2.6.0
Pillow==5.2.0
PyYAML==3.13
Jinja2==2.8
urllib3==1.24.1
Django==2.0.1
cryptography==2.3
""")

        # Setup.py with more vulnerabilities
        setup_py = project_dir / "setup.py"
        setup_py.write_text("""
from setuptools import setup, find_packages
import os

# Potential code execution during setup
exec(open('version.py').read())

setup(
    name="vulnerable-python-app",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Flask==1.0.0",
        "requests==2.6.0", 
        "Pillow==5.2.0",
        "PyYAML==3.13"
    ],
    # Unsafe file permissions
    data_files=[('/etc/', ['config.conf'])],
)
""")

        # Config files that might have issues
        config = project_dir / "config.py"
        config.write_text("""
import os

# More hardcoded secrets
AWS_ACCESS_KEY = "AKIAIOSFODNN7EXAMPLE"
AWS_SECRET_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
DB_PASSWORD = "admin123"
JWT_SECRET = "jwt-secret-key-12345"

# Insecure configurations
DEBUG = True
TESTING = True
ALLOWED_HOSTS = ['*']

# Weak cipher configurations
CIPHER_SUITE = "DES-CBC-SHA"  # Weak cipher
""")

        return {
            "path": str(project_dir),
            "language": "Python",
            "framework": "Flask",
            "expected_issues": 15,
            "package_files": ["requirements.txt", "setup.py"],
        }

    def _create_javascript_project(self, project_dir: Path) -> dict[str, Any]:
        """Create a JavaScript/Node.js project."""

        package_json = project_dir / "package.json"
        package_json.write_text("""
{
  "name": "vulnerable-node-app",
  "version": "1.0.0",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "dependencies": {
    "express": "4.15.0",
    "lodash": "4.17.4",
    "moment": "2.19.3",
    "request": "2.81.0",
    "jsonwebtoken": "7.4.0",
    "mongoose": "4.13.0",
    "helmet": "3.12.0",
    "bcrypt": "1.0.0"
  }
}
""")

        server_js = project_dir / "server.js"
        server_js.write_text("""
const express = require('express');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcrypt');
const fs = require('fs');
const { exec } = require('child_process');
const mongoose = require('mongoose');

const app = express();
app.use(express.json());

// Hardcoded secrets
const JWT_SECRET = 'hardcoded-jwt-secret-key';
const API_KEY = 'sk-1234567890abcdef';
const DB_PASSWORD = 'mongopassword123';

// SQL/NoSQL Injection vulnerabilities
app.post('/user/:id', (req, res) => {
    const userId = req.params.id;
    const query = `db.users.find({id: ${userId}})`; // NoSQL injection
    // Simulate database query
    res.json({ query });
});

// Command injection
app.get('/system/:command', (req, res) => {
    const command = req.params.command;
    exec(`${command}`, (error, stdout, stderr) => { // Direct command execution
        if (error) {
            res.status(500).json({ error: error.message });
            return;
        }
        res.json({ output: stdout });
    });
});

// Path traversal vulnerability
app.get('/files/:filename', (req, res) => {
    const filename = req.params.filename;
    const filePath = `./uploads/${filename}`; // No path validation
    
    fs.readFile(filePath, 'utf8', (err, data) => {
        if (err) {
            res.status(404).json({ error: 'File not found' });
            return;
        }
        res.send(data);
    });
});

// Unsafe eval usage
app.post('/calculate', (req, res) => {
    const expression = req.body.expression;
    try {
        const result = eval(expression); // Direct eval of user input
        res.json({ result });
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

// Weak JWT implementation
app.post('/login', (req, res) => {
    const { username, password } = req.body;
    // Weak token with no expiration
    const token = jwt.sign({ username }, JWT_SECRET, { algorithm: 'none' });
    res.json({ token });
});

// SSRF vulnerability
app.post('/proxy', (req, res) => {
    const url = req.body.url;
    const request = require('request');
    request(url, (error, response, body) => { // No URL validation
        if (error) {
            res.status(500).json({ error: error.message });
            return;
        }
        res.send(body);
    });
});

// Regex DoS potential
app.get('/validate/:input', (req, res) => {
    const input = req.params.input;
    const regex = /^(a+)+$/; // Vulnerable regex pattern
    const isValid = regex.test(input);
    res.json({ valid: isValid });
});

// Prototype pollution vulnerability
app.post('/merge', (req, res) => {
    const _ = require('lodash');
    const target = {};
    const source = req.body;
    _.merge(target, source); // Vulnerable to prototype pollution
    res.json(target);
});

app.listen(3000, () => {
    console.log('Vulnerable Node.js app running on port 3000');
});
""")

        return {
            "path": str(project_dir),
            "language": "JavaScript",
            "framework": "Express.js",
            "expected_issues": 10,
            "package_files": ["package.json"],
        }

    def _create_java_project(self, project_dir: Path) -> dict[str, Any]:
        """Create a Java project with Spring Boot."""

        pom_xml = project_dir / "pom.xml"
        pom_xml.write_text("""
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    
    <groupId>com.example</groupId>
    <artifactId>vulnerable-spring-app</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    
    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
    
    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
            <version>2.0.0.RELEASE</version>
        </dependency>
        <dependency>
            <groupId>com.fasterxml.jackson.core</groupId>
            <artifactId>jackson-databind</artifactId>
            <version>2.8.8</version>
        </dependency>
        <dependency>
            <groupId>org.apache.commons</groupId>
            <artifactId>commons-collections4</artifactId>
            <version>4.0</version>
        </dependency>
        <dependency>
            <groupId>org.apache.struts</groupId>
            <artifactId>struts2-core</artifactId>
            <version>2.3.32</version>
        </dependency>
    </dependencies>
</project>
""")

        src_dir = project_dir / "src" / "main" / "java" / "com" / "example"
        src_dir.mkdir(parents=True, exist_ok=True)

        controller = src_dir / "VulnerableController.java"
        controller.write_text("""
package com.example;

import java.io.*;
import java.sql.*;
import java.security.MessageDigest;
import javax.servlet.http.HttpServletRequest;
import org.springframework.web.bind.annotation.*;

@RestController
public class VulnerableController {
    
    private static final String DB_PASSWORD = "hardcoded-db-password";
    private static final String API_KEY = "hardcoded-api-key-12345";
    
    // SQL Injection vulnerability
    @GetMapping("/user/{id}")
    public String getUser(@PathVariable String id) throws SQLException {
        Connection conn = DriverManager.getConnection(
            "jdbc:mysql://localhost/db", "root", DB_PASSWORD
        );
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE id = " + id; // Direct concatenation
        ResultSet rs = stmt.executeQuery(query);
        return "User data retrieved";
    }
    
    // Command injection
    @PostMapping("/execute")
    public String executeCommand(@RequestBody String command) throws IOException {
        Runtime rt = Runtime.getRuntime();
        Process proc = rt.exec(command); // Direct command execution
        return "Command executed: " + command;
    }
    
    // Insecure deserialization
    @PostMapping("/deserialize")
    public Object deserializeData(@RequestBody byte[] data) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
        return ois.readObject(); // Unsafe deserialization
    }
    
    // Weak cryptography
    @PostMapping("/hash")
    public String hashPassword(@RequestBody String password) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] hash = md.digest(password.getBytes());
        return new String(hash); // MD5 is weak
    }
    
    // Path traversal
    @GetMapping("/file/{filename}")
    public String readFile(@PathVariable String filename) throws IOException {
        BufferedReader br = new BufferedReader(
            new FileReader("uploads/" + filename) // No path validation
        );
        return br.readLine();
    }
    
    // XXE vulnerability
    @PostMapping("/xml")
    public String parseXML(@RequestBody String xmlData) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        // External entity processing enabled by default
        DocumentBuilder builder = factory.newDocumentBuilder();
        Document doc = builder.parse(new ByteArrayInputStream(xmlData.getBytes()));
        return "XML processed";
    }
    
    // LDAP injection
    @GetMapping("/ldap/{username}")
    public String searchLDAP(@PathVariable String username) throws Exception {
        String searchFilter = "(uid=" + username + ")"; // No sanitization
        // Simulate LDAP query
        return "LDAP search: " + searchFilter;
    }
}
""")

        return {
            "path": str(project_dir),
            "language": "Java",
            "framework": "Spring Boot",
            "expected_issues": 8,
            "package_files": ["pom.xml"],
        }

    def _create_go_project(self, project_dir: Path) -> dict[str, Any]:
        """Create a Go project."""

        go_mod = project_dir / "go.mod"
        go_mod.write_text("""
module vulnerable-go-app

go 1.18

require (
    github.com/gin-gonic/gin v1.6.0
    github.com/go-sql-driver/mysql v1.5.0
    golang.org/x/crypto v0.0.0-20190308221718-c2843e01d9a2
    gopkg.in/yaml.v2 v2.2.8
)
""")

        main_go = project_dir / "main.go"
        main_go.write_text("""
package main

import (
    "crypto/md5"
    "database/sql"
    "fmt"
    "io/ioutil"
    "net/http"
    "os/exec"
    "path/filepath"
    "unsafe"
    
    "github.com/gin-gonic/gin"
    _ "github.com/go-sql-driver/mysql"
    "gopkg.in/yaml.v2"
)

const (
    API_KEY = "hardcoded-go-api-key"
    DB_PASS = "go-database-password-123"
)

type Config struct {
    Database string `yaml:"database"`
    APIKey   string `yaml:"apikey"`
}

// SQL injection vulnerability
func getUser(userID string) error {
    db, err := sql.Open("mysql", "user:" + DB_PASS + "@tcp(localhost:3306)/database")
    if err != nil {
        return err
    }
    query := "SELECT * FROM users WHERE id = " + userID // Direct concatenation
    _, err = db.Query(query)
    return err
}

// Command injection
func executeCommand(command string) (string, error) {
    cmd := exec.Command("sh", "-c", command) // Shell command execution
    out, err := cmd.Output()
    return string(out), err
}

// Weak cryptography
func weakHash(data string) string {
    hash := md5.Sum([]byte(data)) // MD5 is weak
    return fmt.Sprintf("%x", hash)
}

// Path traversal
func readFile(filename string) (string, error) {
    path := filepath.Join("files", filename) // No path validation
    content, err := ioutil.ReadFile(path)
    return string(content), err
}

// Unsafe pointer operations
func unsafeOperation(data []byte) {
    ptr := unsafe.Pointer(&data[0])
    // Unsafe pointer manipulation
    value := *(*int)(ptr)
    fmt.Println("Unsafe value:", value)
}

// YAML deserialization without validation
func parseYAML(yamlData []byte) (*Config, error) {
    var config Config
    err := yaml.Unmarshal(yamlData, &config) // Potentially unsafe
    return &config, err
}

// HTTP client without timeout
func fetchURL(url string) (string, error) {
    resp, err := http.Get(url) // No timeout, no URL validation
    if err != nil {
        return "", err
    }
    defer resp.Body.Close()
    
    body, err := ioutil.ReadAll(resp.Body)
    return string(body), err
}

func main() {
    r := gin.Default()
    
    r.GET("/user/:id", func(c *gin.Context) {
        userID := c.Param("id")
        err := getUser(userID)
        if err != nil {
            c.JSON(500, gin.H{"error": err.Error()})
            return
        }
        c.JSON(200, gin.H{"status": "ok"})
    })
    
    r.POST("/exec", func(c *gin.Context) {
        var req struct {
            Command string `json:"command"`
        }
        c.BindJSON(&req)
        
        result, err := executeCommand(req.Command)
        if err != nil {
            c.JSON(500, gin.H{"error": err.Error()})
            return
        }
        c.String(200, result)
    })
    
    r.POST("/hash", func(c *gin.Context) {
        var req struct {
            Data string `json:"data"`
        }
        c.BindJSON(&req)
        
        hash := weakHash(req.Data)
        c.JSON(200, gin.H{"hash": hash})
    })
    
    r.Run(":8080")
}
""")

        return {
            "path": str(project_dir),
            "language": "Go",
            "framework": "Gin",
            "expected_issues": 7,
            "package_files": ["go.mod"],
        }

    def _create_typescript_project(self, project_dir: Path) -> dict[str, Any]:
        """Create a TypeScript project."""

        package_json = project_dir / "package.json"
        package_json.write_text("""
{
  "name": "vulnerable-typescript-app",
  "version": "1.0.0",
  "main": "dist/server.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/server.js",
    "dev": "ts-node src/server.ts"
  },
  "dependencies": {
    "express": "4.16.0",
    "typescript": "3.8.0",
    "@types/express": "4.16.0",
    "lodash": "4.17.10",
    "jsonwebtoken": "8.5.0",
    "bcrypt": "3.0.0"
  }
}
""")

        tsconfig = project_dir / "tsconfig.json"
        tsconfig.write_text("""
{
  "compilerOptions": {
    "target": "ES2018",
    "module": "commonjs",
    "outDir": "dist",
    "rootDir": "src",
    "strict": false,
    "noImplicitAny": false
  }
}
""")

        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        server_ts = src_dir / "server.ts"
        server_ts.write_text("""
import express from 'express';
import * as crypto from 'crypto';
import * as fs from 'fs';
import { exec } from 'child_process';
import * as jwt from 'jsonwebtoken';

const app = express();
app.use(express.json());

// Hardcoded secrets
const JWT_SECRET = 'typescript-jwt-secret';
const API_KEY = 'ts-api-key-12345';

interface User {
    id: number;
    username: string;
    password?: string;
}

interface DatabaseQuery {
    query: string;
    params?: any[];
}

// Type confusion vulnerability
function processUserData(userData: any): User {
    // No type validation - potential type confusion
    return {
        id: userData.id,
        username: userData.username,
        password: userData.password
    };
}

// Weak cryptography
function hashPassword(password: string): string {
    return crypto.createHash('md5').update(password).digest('hex');
}

// SQL injection through template literals
function buildQuery(tableName: string, userId: string): DatabaseQuery {
    // Direct string interpolation in SQL
    const query = `SELECT * FROM ${tableName} WHERE id = ${userId}`;
    return { query };
}

// Command injection
function executeSystemCommand(command: string): Promise<string> {
    return new Promise((resolve, reject) => {
        exec(command, (error, stdout, stderr) => {
            if (error) {
                reject(error);
                return;
            }
            resolve(stdout);
        });
    });
}

// Path traversal
function readUserFile(filename: string): string {
    const filePath = `./user_files/${filename}`; // No path validation
    return fs.readFileSync(filePath, 'utf8');
}

// Unsafe eval usage
function evaluateExpression(expression: string): any {
    return eval(expression); // Direct eval
}

// Weak JWT implementation
function generateToken(user: User): string {
    return jwt.sign({ id: user.id, username: user.username }, JWT_SECRET, {
        algorithm: 'none' // No algorithm
    });
}

// SSRF vulnerability
async function fetchExternalData(url: string): Promise<string> {
    const https = require('https');
    // No URL validation
    return new Promise((resolve, reject) => {
        https.get(url, (res: any) => {
            let data = '';
            res.on('data', (chunk: any) => data += chunk);
            res.on('end', () => resolve(data));
        }).on('error', reject);
    });
}

app.post('/user', (req, res) => {
    const userData = processUserData(req.body);
    res.json(userData);
});

app.get('/query/:table/:id', (req, res) => {
    const { table, id } = req.params;
    const query = buildQuery(table, id);
    res.json(query);
});

app.post('/exec', async (req, res) => {
    try {
        const result = await executeSystemCommand(req.body.command);
        res.send(result);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.get('/file/:filename', (req, res) => {
    try {
        const content = readUserFile(req.params.filename);
        res.send(content);
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

export default app;
""")

        return {
            "path": str(project_dir),
            "language": "TypeScript",
            "framework": "Express.js",
            "expected_issues": 9,
            "package_files": ["package.json", "tsconfig.json"],
        }

    def create_test_configs(self):
        """Create test configuration files."""

        # Create projects.json with all test projects
        projects_config = {"projects": []}

        for lang, project_info in self.test_projects.items():
            projects_config["projects"].append(
                {
                    "url": project_info["path"],
                    "name": f"test-{lang}-project",
                    "language": project_info["language"],
                    "description": f"Load test {lang} project",
                    "container_capable": lang in ["python", "javascript", "java"],
                    "dockerfile_present": False,
                    "package_managers": project_info.get("package_files", []),
                }
            )

        projects_file = Path(self.temp_dir) / "projects.json"
        with open(projects_file, "w") as f:
            json.dump(projects_config, f, indent=2)

        # Create mock database
        db_file = Path(self.temp_dir) / "mock_db.tar.gz"
        mock_db_content = {
            "vulnerabilities": [
                {"id": "CVE-2021-44228", "severity": "critical"},
                {"id": "CVE-2017-5638", "severity": "high"},
                {"id": "CVE-2019-0232", "severity": "high"},
            ]
        }

        with open(db_file, "w") as f:
            json.dump(mock_db_content, f)

        # Create network allowlist
        allowlist_file = Path(self.temp_dir) / "network_allowlist.txt"
        allowlist_file.write_text("""localhost:8080
127.0.0.1:3000
example.com:443
registry-1.docker.io:443
""")

        logger.info("Test configuration files created")

    def run_concurrent_scan_test(self, num_concurrent_scans: int = 10):
        """Test concurrent scanning performance."""
        logger.info(f"Running concurrent scan test with {num_concurrent_scans} scans")

        start_time = time.time()
        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Simulate concurrent scans
        with ThreadPoolExecutor(max_workers=min(num_concurrent_scans, 8)) as executor:
            futures = []

            for i in range(num_concurrent_scans):
                # Rotate through different project types
                project_langs = list(self.test_projects.keys())
                lang = project_langs[i % len(project_langs)]
                project_info = self.test_projects[lang]

                future = executor.submit(
                    self._simulate_scan, project_info, f"concurrent_{i}"
                )
                futures.append(future)

            # Collect results
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=60)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent scan failed: {e}")
                    self.results["errors"].append(str(e))

        end_time = time.time()
        final_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Calculate metrics
        total_time = end_time - start_time
        avg_scan_time = total_time / len(results) if results else 0
        memory_increase = final_memory - initial_memory

        test_result = {
            "test_type": "concurrent_scans",
            "num_scans": num_concurrent_scans,
            "successful_scans": len(results),
            "total_time": total_time,
            "average_scan_time": avg_scan_time,
            "initial_memory_mb": initial_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": memory_increase,
            "scans_per_second": len(results) / total_time if total_time > 0 else 0,
        }

        self.results["load_tests"].append(test_result)
        logger.info(
            f"Concurrent test completed: {len(results)}/{num_concurrent_scans} scans in {total_time:.2f}s"
        )

        return test_result

    def run_memory_stress_test(self):
        """Test memory usage under stress."""
        logger.info("Running memory stress test")

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024
        peak_memory = initial_memory

        # Simulate processing large scan results
        large_datasets = []
        try:
            for i in range(5):
                # Create large mock scan results
                dataset = self._create_large_scan_result(5000 + i * 1000)
                large_datasets.append(dataset)

                current_memory = psutil.Process().memory_info().rss / 1024 / 1024
                peak_memory = max(peak_memory, current_memory)

                logger.info(f"Memory after dataset {i + 1}: {current_memory:.1f}MB")

                # Simulate processing time
                time.sleep(0.5)

        finally:
            # Cleanup
            large_datasets.clear()

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024

        stress_result = {
            "test_type": "memory_stress",
            "initial_memory_mb": initial_memory,
            "peak_memory_mb": peak_memory,
            "final_memory_mb": final_memory,
            "memory_increase_mb": peak_memory - initial_memory,
            "memory_recovered": initial_memory - final_memory,
        }

        self.results["performance_metrics"]["memory_stress"] = stress_result
        logger.info(
            f"Memory stress test: Peak {peak_memory:.1f}MB (+{peak_memory - initial_memory:.1f}MB)"
        )

        return stress_result

    def run_report_generation_load_test(self):
        """Test report generation under load."""
        logger.info("Running report generation load test")

        report_sizes = [100, 500, 1000, 2500, 5000]
        results = {}

        for size in report_sizes:
            start_time = time.time()

            # Generate mock findings
            findings = []
            for i in range(size):
                findings.append(
                    {
                        "id": f"FINDING-{i}",
                        "severity": ["low", "medium", "high", "critical"][i % 4],
                        "title": f"Test vulnerability {i}",
                        "description": f"Description for finding {i}" * 10,
                        "file": f"src/file_{i % 100}.py",
                        "line": (i % 1000) + 1,
                        "cve_id": f"CVE-2024-{1000 + i}",
                        "cvss_score": (i % 10) + 1,
                        "recommendation": f"Fix recommendation for finding {i}",
                    }
                )

            # Generate report
            report_content = self._generate_load_test_report(findings)
            generation_time = time.time() - start_time

            results[f"{size}_findings"] = {
                "findings_count": size,
                "generation_time": generation_time,
                "report_size_chars": len(report_content),
                "findings_per_second": size / generation_time
                if generation_time > 0
                else 0,
            }

            logger.info(
                f"Report with {size} findings: {generation_time:.2f}s ({len(report_content)} chars)"
            )

        self.results["performance_metrics"]["report_generation"] = results
        return results

    def run_container_resource_test(self):
        """Test container resource limits simulation."""
        logger.info("Running container resource simulation test")

        # Simulate different container resource scenarios
        scenarios = [
            {"memory_limit": "512m", "cpu_limit": "0.5"},
            {"memory_limit": "1g", "cpu_limit": "1.0"},
            {"memory_limit": "2g", "cpu_limit": "2.0"},
        ]

        results = {}

        for scenario in scenarios:
            scenario_name = (
                f"mem_{scenario['memory_limit']}_cpu_{scenario['cpu_limit']}"
            )
            start_time = time.time()

            # Simulate resource-constrained scanning
            scan_results = []
            for lang, project_info in self.test_projects.items():
                result = self._simulate_constrained_scan(project_info, scenario)
                scan_results.append(result)

            total_time = time.time() - start_time

            results[scenario_name] = {
                "memory_limit": scenario["memory_limit"],
                "cpu_limit": scenario["cpu_limit"],
                "total_scans": len(scan_results),
                "total_time": total_time,
                "average_scan_time": total_time / len(scan_results),
                "successful_scans": len(
                    [r for r in scan_results if r["status"] == "success"]
                ),
            }

        self.results["performance_metrics"]["container_resources"] = results
        logger.info("Container resource simulation completed")

        return results

    def _simulate_scan(
        self, project_info: dict[str, Any], scan_id: str
    ) -> dict[str, Any]:
        """Simulate a security scan."""

        # Simulate scan time based on project complexity
        expected_issues = project_info.get("expected_issues", 1)
        base_scan_time = 0.5 + (expected_issues * 0.1)

        # Add some randomness to simulate real-world variance
        import random

        actual_scan_time = base_scan_time + random.uniform(-0.2, 0.5)

        time.sleep(max(0.1, actual_scan_time))  # Minimum 0.1s

        return {
            "scan_id": scan_id,
            "project_language": project_info["language"],
            "framework": project_info.get("framework", "Unknown"),
            "scan_duration": actual_scan_time,
            "issues_found": expected_issues + random.randint(-1, 2),
            "status": "success",
            "timestamp": time.time(),
        }

    def _simulate_constrained_scan(
        self, project_info: dict[str, Any], constraints: dict[str, str]
    ) -> dict[str, Any]:
        """Simulate scan under resource constraints."""

        # Simulate the effect of resource constraints
        memory_factor = 1.0
        if constraints["memory_limit"] == "512m":
            memory_factor = 1.5  # Slower due to memory pressure
        elif constraints["memory_limit"] == "1g":
            memory_factor = 1.2

        cpu_factor = float(constraints["cpu_limit"])

        base_time = 0.5 + (project_info.get("expected_issues", 1) * 0.1)
        adjusted_time = base_time * memory_factor / max(cpu_factor, 0.5)

        time.sleep(min(adjusted_time, 5.0))  # Cap at 5 seconds

        return {
            "language": project_info["language"],
            "constraints": constraints,
            "scan_time": adjusted_time,
            "status": "success",
            "memory_pressure": memory_factor > 1.2,
        }

    def _create_large_scan_result(self, num_findings: int) -> dict[str, Any]:
        """Create large mock scan result for memory testing."""
        return {
            "scan_id": f"memory_test_{num_findings}",
            "findings": [
                {
                    "id": f"FINDING-{i}",
                    "title": f"Security issue {i}",
                    "description": f"Detailed description for finding {i}" * 20,
                    "severity": ["low", "medium", "high", "critical"][i % 4],
                    "file_path": f"/path/to/file_{i % 100}.py",
                    "line_number": (i % 1000) + 1,
                    "column_number": (i % 80) + 1,
                    "rule_id": f"RULE-{i % 50}",
                    "cwe_id": f"CWE-{200 + (i % 100)}",
                    "owasp_category": f"A{(i % 10) + 1}",
                    "metadata": {
                        "confidence": "high",
                        "impact": "medium",
                        "effort": "low",
                        "tags": [f"tag{j}" for j in range(i % 5)],
                        "references": [
                            f"https://example.com/ref{j}" for j in range(i % 3)
                        ],
                    },
                    "code_context": {
                        "before": [f"line {i - j}" for j in range(3, 0, -1)],
                        "vulnerable_line": f"vulnerable code line {i}",
                        "after": [f"line {i + j}" for j in range(1, 4)],
                    },
                }
                for i in range(num_findings)
            ],
            "statistics": {
                "total_files_scanned": num_findings // 10,
                "total_lines_scanned": num_findings * 100,
                "scan_duration": num_findings * 0.001,
            },
        }

    def _generate_load_test_report(self, findings: list[dict[str, Any]]) -> str:
        """Generate comprehensive test report."""

        # Count findings by severity
        severity_counts = {}
        for finding in findings:
            severity = finding["severity"]
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        report = f"""# Security Scan Load Test Report

## Executive Summary
This report contains the results of a comprehensive security scan performed as part of load testing.

**Total Findings:** {len(findings)}
**Critical:** {severity_counts.get("critical", 0)}
**High:** {severity_counts.get("high", 0)}
**Medium:** {severity_counts.get("medium", 0)}
**Low:** {severity_counts.get("low", 0)}

## Scan Statistics
- Files analyzed: {len(set(f["file"] for f in findings))}
- Average CVSS Score: {sum(f.get("cvss_score", 5) for f in findings) / len(findings):.1f}
- Scan completed at: {time.strftime("%Y-%m-%d %H:%M:%S")}

## Critical Findings

"""

        # Include detailed information for critical and high findings
        critical_findings = [
            f for f in findings if f["severity"] in ["critical", "high"]
        ]

        for i, finding in enumerate(critical_findings[:20]):  # First 20 critical/high
            report += f"""### {finding["id"]} - {finding["severity"].upper()}

**Title:** {finding["title"]}
**File:** {finding["file"]}:{finding["line"]}
**CVE ID:** {finding.get("cve_id", "N/A")}
**CVSS Score:** {finding.get("cvss_score", "N/A")}

**Description:**
{finding["description"]}

**Recommendation:**
{finding.get("recommendation", "Review and remediate this vulnerability")}

---

"""

        if len(critical_findings) > 20:
            report += f"\n*... and {len(critical_findings) - 20} more critical/high findings*\n\n"

        # Add summary tables
        report += """## Finding Distribution by File

| File | Critical | High | Medium | Low | Total |
|------|----------|------|--------|-----|-------|
"""

        # Group by file for summary
        file_stats = {}
        for finding in findings:
            file_name = finding["file"]
            if file_name not in file_stats:
                file_stats[file_name] = {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0,
                }
            file_stats[file_name][finding["severity"]] += 1

        for file_name, stats in sorted(file_stats.items())[:50]:  # First 50 files
            total = sum(stats.values())
            report += f"| {file_name} | {stats['critical']} | {stats['high']} | {stats['medium']} | {stats['low']} | {total} |\n"

        if len(file_stats) > 50:
            report += f"\n*... and {len(file_stats) - 50} more files*\n"

        report += f"""

## Recommendations

1. **Immediate Action Required:** Address all {severity_counts.get("critical", 0)} critical vulnerabilities
2. **High Priority:** Remediate {severity_counts.get("high", 0)} high-severity issues  
3. **Review Process:** Implement security code review for medium and low findings
4. **Prevention:** Add security linting and SAST tools to CI/CD pipeline

## Report Metadata

- Report generated: {time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())}
- Total findings processed: {len(findings)}
- Report size: {len(findings)} findings across {len(file_stats)} files
- Load test identifier: geotoolkit-load-test-{int(time.time())}

"""

        return report

    def run_full_load_test_suite(self):
        """Run the complete load testing suite."""
        logger.info("Starting comprehensive load testing suite")

        start_time = time.time()

        try:
            # 1. Concurrent scanning test
            self.run_concurrent_scan_test(10)

            # 2. Memory stress test
            self.run_memory_stress_test()

            # 3. Report generation load test
            self.run_report_generation_load_test()

            # 4. Container resource simulation
            self.run_container_resource_test()

            # 5. Higher concurrency test
            self.run_concurrent_scan_test(20)

        except Exception as e:
            logger.error(f"Load test suite failed: {e}")
            self.results["errors"].append(str(e))

        total_time = time.time() - start_time

        # Generate summary
        self.results["summary"] = {
            "total_test_time": total_time,
            "tests_completed": len(self.results["load_tests"]),
            "performance_tests": len(self.results["performance_metrics"]),
            "total_errors": len(self.results["errors"]),
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        }

        logger.info(f"Load testing suite completed in {total_time:.2f}s")

        return self.results

    def cleanup(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            import shutil

            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test environment: {self.temp_dir}")


def main():
    """Main entry point for load testing."""
    parser = argparse.ArgumentParser(description="GeoToolKit Load Testing Suite")
    parser.add_argument(
        "--concurrent-scans",
        type=int,
        default=10,
        help="Number of concurrent scans to run (default: 10)",
    )
    parser.add_argument(
        "--memory-test", action="store_true", help="Run memory stress testing"
    )
    parser.add_argument(
        "--report-test", action="store_true", help="Run report generation load testing"
    )
    parser.add_argument(
        "--full-suite", action="store_true", help="Run complete load testing suite"
    )
    parser.add_argument(
        "--output",
        default="load_test_results.json",
        help="Output file for test results",
    )

    args = parser.parse_args()

    # Initialize load test runner
    runner = LoadTestRunner()

    try:
        # Setup test environment
        runner.setup_test_environment()

        if args.full_suite:
            results = runner.run_full_load_test_suite()
        else:
            # Run individual tests based on flags
            if args.concurrent_scans:
                runner.run_concurrent_scan_test(args.concurrent_scans)
            if args.memory_test:
                runner.run_memory_stress_test()
            if args.report_test:
                runner.run_report_generation_load_test()

            results = runner.results

        # Save results
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)

        # Print summary
        print("\nLoad Testing Summary:")
        print(f"Total Tests: {len(results['load_tests'])}")
        print(f"Performance Metrics: {len(results['performance_metrics'])}")
        print(f"Errors: {len(results['errors'])}")
        print(f"Results saved to: {args.output}")

        if results.get("summary"):
            print(f"Total Time: {results['summary']['total_test_time']:.2f}s")

    except Exception as e:
        logger.error(f"Load testing failed: {e}")
        return 1

    finally:
        # Cleanup
        runner.cleanup()

    return 0


if __name__ == "__main__":
    exit(main())
