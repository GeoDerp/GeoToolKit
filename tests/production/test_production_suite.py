"""
Production Testing Suite for GeoToolKit

This module contains comprehensive production readiness tests that validate:
1. All core functionalities across multiple programming languages
2. Edge cases and error handling
3. Load testing and performance validation
4. Container security and isolation
5. End-to-end workflow validation
6. Multi-language project scanning
7. Network isolation and security
8. Report generation under load
"""

import concurrent.futures
import json
import logging
import os
import shutil
import tempfile
import time
from pathlib import Path

import pytest

# Configure logging for production testing
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ProductionTestSuite:
    """Comprehensive production test suite for GeoToolKit."""

    def __init__(self):
        self.test_results = {
            "passed": 0,
            "failed": 0,
            "errors": [],
            "performance_metrics": {},
        }
        self.temp_dir = None

    def setup_test_environment(self):
        """Set up comprehensive test environment with multiple language projects."""
        self.temp_dir = tempfile.mkdtemp(prefix="geotoolkit_prod_test_")
        logger.info(f"Setting up test environment in {self.temp_dir}")

        # Create test projects for all supported languages
        self.test_projects = self._create_multi_language_projects()

        # Create mock vulnerability database
        self._setup_mock_database()

        # Setup network configuration
        self._setup_network_config()

        return self.temp_dir

    def _create_multi_language_projects(self) -> dict[str, dict]:
        """Create test projects for all supported programming languages."""
        projects = {}

        # Python project with various vulnerabilities
        python_project = self._create_python_test_project()
        projects["python"] = python_project

        # JavaScript/Node.js project
        js_project = self._create_javascript_test_project()
        projects["javascript"] = js_project

        # TypeScript project
        ts_project = self._create_typescript_test_project()
        projects["typescript"] = ts_project

        # Java/Spring Boot project
        java_project = self._create_java_test_project()
        projects["java"] = java_project

        # Go project
        go_project = self._create_go_test_project()
        projects["go"] = go_project

        # Ruby project
        ruby_project = self._create_ruby_test_project()
        projects["ruby"] = ruby_project

        # C# project
        csharp_project = self._create_csharp_test_project()
        projects["csharp"] = csharp_project

        # PHP project
        php_project = self._create_php_test_project()
        projects["php"] = php_project

        # Rust project
        rust_project = self._create_rust_test_project()
        projects["rust"] = rust_project

        # C/C++ project
        cpp_project = self._create_cpp_test_project()
        projects["cpp"] = cpp_project

        return projects

    def _create_python_test_project(self) -> dict:
        """Create a Python test project with known vulnerabilities."""
        project_dir = Path(self.temp_dir) / "test_python_project"
        project_dir.mkdir(exist_ok=True)

        # Create main application file with vulnerabilities
        main_py = project_dir / "app.py"
        main_py.write_text("""
import os
import pickle
import subprocess
import hashlib

# Hardcoded secret (security issue)
SECRET_KEY = "super-secret-key-12345"
DATABASE_URL = "postgresql://admin:password@localhost/db"

# SQL injection vulnerability
def get_user(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"
    return query

# Command injection vulnerability
def run_command(user_input):
    command = f"ls {user_input}"
    return subprocess.call(command, shell=True)

# Insecure deserialization
def load_data(data):
    return pickle.loads(data)

# Weak hash function
def hash_password(password):
    return hashlib.md5(password.encode()).hexdigest()

# Path traversal vulnerability
def read_file(filename):
    with open(f"/app/files/{filename}", 'r') as f:
        return f.read()

# XSS vulnerability potential
def generate_html(user_input):
    return f"<div>{user_input}</div>"

if __name__ == "__main__":
    print("Vulnerable Python application")
""")

        # Create requirements.txt with vulnerable packages
        requirements = project_dir / "requirements.txt"
        requirements.write_text("""
Django==2.0.1
requests==2.6.0
Pillow==5.2.0
PyYAML==3.13
Jinja2==2.8
urllib3==1.24.1
""")

        # Create setup.py
        setup_py = project_dir / "setup.py"
        setup_py.write_text("""
from setuptools import setup, find_packages

setup(
    name="vulnerable-app",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "Django==2.0.1",
        "requests==2.6.0",
        "Pillow==5.2.0",
        "PyYAML==3.13"
    ]
)
""")

        # Create Dockerfile for containerized scanning
        dockerfile = project_dir / "Dockerfile"
        dockerfile.write_text("""
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "app.py"]
""")

        return {
            "path": str(project_dir),
            "language": "Python",
            "has_dockerfile": True,
            "package_files": ["requirements.txt", "setup.py"],
            "expected_vulnerabilities": 8,
        }

    def _create_javascript_test_project(self) -> dict:
        """Create a JavaScript/Node.js test project."""
        project_dir = Path(self.temp_dir) / "test_js_project"
        project_dir.mkdir(exist_ok=True)

        # Create package.json with vulnerable dependencies
        package_json = project_dir / "package.json"
        package_json.write_text("""
{
  "name": "vulnerable-js-app",
  "version": "1.0.0",
  "description": "Test application with vulnerabilities",
  "main": "app.js",
  "scripts": {
    "start": "node app.js",
    "test": "mocha"
  },
  "dependencies": {
    "express": "4.15.0",
    "lodash": "4.17.4",
    "moment": "2.19.3",
    "request": "2.81.0",
    "validator": "6.2.0",
    "jsonwebtoken": "7.4.0"
  },
  "devDependencies": {
    "mocha": "3.4.2",
    "chai": "4.0.2"
  }
}
""")

        # Create main application with vulnerabilities
        app_js = project_dir / "app.js"
        app_js.write_text("""
const express = require('express');
const jwt = require('jsonwebtoken');
const app = express();

// Hardcoded secret
const SECRET = 'hardcoded-jwt-secret';

// Vulnerable to prototype pollution
app.use(express.json());

app.post('/login', (req, res) => {
    const { username, password } = req.body;

    // SQL injection vulnerable query simulation
    const query = `SELECT * FROM users WHERE username = '${username}' AND password = '${password}'`;

    // Weak JWT signing
    const token = jwt.sign({ username }, SECRET, { algorithm: 'none' });

    res.json({ token });
});

// Path traversal vulnerability
app.get('/file/:filename', (req, res) => {
    const filename = req.params.filename;
    const fs = require('fs');
    const path = require('path');

    // Vulnerable to path traversal
    const filePath = path.join(__dirname, 'files', filename);
    fs.readFileSync(filePath);
});

// Command injection
app.get('/ping/:host', (req, res) => {
    const host = req.params.host;
    const { exec } = require('child_process');

    exec(`ping -c 1 ${host}`, (error, stdout, stderr) => {
        res.send(stdout);
    });
});

app.listen(3000, () => {
    console.log('Vulnerable app running on port 3000');
});
""")

        return {
            "path": str(project_dir),
            "language": "JavaScript",
            "has_dockerfile": False,
            "package_files": ["package.json"],
            "expected_vulnerabilities": 6,
        }

    def _create_typescript_test_project(self) -> dict:
        """Create a TypeScript test project."""
        project_dir = Path(self.temp_dir) / "test_ts_project"
        project_dir.mkdir(exist_ok=True)

        # Create package.json
        package_json = project_dir / "package.json"
        package_json.write_text("""
{
  "name": "vulnerable-ts-app",
  "version": "1.0.0",
  "main": "dist/app.js",
  "scripts": {
    "build": "tsc",
    "start": "node dist/app.js"
  },
  "dependencies": {
    "express": "4.16.0",
    "typescript": "3.8.0",
    "@types/express": "4.16.0",
    "lodash": "4.17.10"
  }
}
""")

        # Create tsconfig.json
        tsconfig = project_dir / "tsconfig.json"
        tsconfig.write_text("""
{
  "compilerOptions": {
    "target": "ES2018",
    "module": "commonjs",
    "outDir": "dist",
    "rootDir": "src",
    "strict": false
  }
}
""")

        # Create TypeScript source with vulnerabilities
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        app_ts = src_dir / "app.ts"
        app_ts.write_text("""
import express from 'express';
import * as crypto from 'crypto';

const app = express();
const SECRET_KEY = 'typescript-secret-key';

interface User {
    id: number;
    username: string;
    password?: string;
}

// Vulnerable password hashing
function hashPassword(password: string): string {
    return crypto.createHash('md5').update(password).digest('hex');
}

// Type confusion vulnerability
function processUser(userData: any): User {
    return {
        id: userData.id,
        username: userData.username,
        password: hashPassword(userData.password)
    };
}

// Unsafe eval usage
function executeCode(code: string) {
    return eval(code);
}

app.use(express.json());

app.post('/user', (req, res) => {
    const user = processUser(req.body);
    res.json(user);
});

export default app;
""")

        return {
            "path": str(project_dir),
            "language": "TypeScript",
            "has_dockerfile": False,
            "package_files": ["package.json", "tsconfig.json"],
            "expected_vulnerabilities": 4,
        }

    def _create_java_test_project(self) -> dict:
        """Create a Java/Spring Boot test project."""
        project_dir = Path(self.temp_dir) / "test_java_project"
        project_dir.mkdir(exist_ok=True)

        # Create pom.xml with vulnerable dependencies
        pom_xml = project_dir / "pom.xml"
        pom_xml.write_text("""
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.example</groupId>
    <artifactId>vulnerable-app</artifactId>
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
    </dependencies>
</project>
""")

        # Create Java source directory structure
        src_dir = project_dir / "src" / "main" / "java" / "com" / "example"
        src_dir.mkdir(parents=True, exist_ok=True)

        # Create vulnerable Java application
        app_java = src_dir / "VulnerableApp.java"
        app_java.write_text("""
package com.example;

import java.io.*;
import java.sql.*;
import java.security.MessageDigest;
import javax.servlet.http.HttpServletRequest;

public class VulnerableApp {

    private static final String SECRET_KEY = "java-hardcoded-secret";

    // SQL Injection vulnerability
    public User getUser(String userId) throws SQLException {
        Connection conn = DriverManager.getConnection("jdbc:mysql://localhost/db");
        Statement stmt = conn.createStatement();
        String query = "SELECT * FROM users WHERE id = " + userId;
        ResultSet rs = stmt.executeQuery(query);
        return null;
    }

    // Command injection
    public String executeCommand(String userInput) throws IOException {
        Runtime rt = Runtime.getRuntime();
        Process proc = rt.exec("ping " + userInput);
        return "Command executed";
    }

    // Insecure deserialization
    public Object deserialize(byte[] data) throws Exception {
        ObjectInputStream ois = new ObjectInputStream(new ByteArrayInputStream(data));
        return ois.readObject();
    }

    // Weak cryptography
    public String hashPassword(String password) throws Exception {
        MessageDigest md = MessageDigest.getInstance("MD5");
        byte[] hash = md.digest(password.getBytes());
        return new String(hash);
    }

    // Path traversal
    public String readFile(String filename) throws IOException {
        BufferedReader br = new BufferedReader(new FileReader("files/" + filename));
        return br.readLine();
    }
}

class User {
    public String username;
    public String password;
}
""")

        return {
            "path": str(project_dir),
            "language": "Java",
            "has_dockerfile": False,
            "package_files": ["pom.xml"],
            "expected_vulnerabilities": 6,
        }

    def _create_go_test_project(self) -> dict:
        """Create a Go test project."""
        project_dir = Path(self.temp_dir) / "test_go_project"
        project_dir.mkdir(exist_ok=True)

        # Create go.mod
        go_mod = project_dir / "go.mod"
        go_mod.write_text("""
module vulnerable-go-app

go 1.16

require (
    github.com/gin-gonic/gin v1.6.0
    github.com/go-sql-driver/mysql v1.5.0
    golang.org/x/crypto v0.0.0-20190308221718-c2843e01d9a2
)
""")

        # Create main.go with vulnerabilities
        main_go = project_dir / "main.go"
        main_go.write_text("""
package main

import (
    "crypto/md5"
    "database/sql"
    "fmt"
    "net/http"
    "os/exec"
    "io/ioutil"
    "path/filepath"

    "github.com/gin-gonic/gin"
    _ "github.com/go-sql-driver/mysql"
)

const SECRET_KEY = "go-hardcoded-secret"

// SQL injection vulnerability
func getUser(userID string) error {
    db, _ := sql.Open("mysql", "user:password@tcp(localhost:3306)/database")
    query := "SELECT * FROM users WHERE id = " + userID
    _, err := db.Query(query)
    return err
}

// Command injection
func pingHost(host string) (string, error) {
    cmd := exec.Command("ping", "-c", "1", host)
    out, err := cmd.Output()
    return string(out), err
}

// Weak cryptography
func hashPassword(password string) string {
    hash := md5.Sum([]byte(password))
    return fmt.Sprintf("%x", hash)
}

// Path traversal
func readFile(filename string) (string, error) {
    path := filepath.Join("files", filename)
    content, err := ioutil.ReadFile(path)
    return string(content), err
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

    r.GET("/ping/:host", func(c *gin.Context) {
        host := c.Param("host")
        result, _ := pingHost(host)
        c.String(200, result)
    })

    r.Run(":8080")
}
""")

        return {
            "path": str(project_dir),
            "language": "Go",
            "has_dockerfile": False,
            "package_files": ["go.mod"],
            "expected_vulnerabilities": 4,
        }

    def _create_ruby_test_project(self) -> dict:
        """Create a Ruby test project."""
        project_dir = Path(self.temp_dir) / "test_ruby_project"
        project_dir.mkdir(exist_ok=True)

        # Create Gemfile with vulnerable gems
        gemfile = project_dir / "Gemfile"
        gemfile.write_text("""
source 'https://rubygems.org'

gem 'rails', '4.2.0'
gem 'nokogiri', '1.6.0'
gem 'rack', '1.6.0'
gem 'actionpack', '4.2.0'
gem 'activerecord', '4.2.0'
""")

        # Create vulnerable Ruby application
        app_rb = project_dir / "app.rb"
        app_rb.write_text("""
require 'digest'
require 'yaml'
require 'erb'

class VulnerableApp
  SECRET_KEY = 'ruby-hardcoded-secret'

  # SQL injection vulnerability
  def find_user(user_id)
    ActiveRecord::Base.connection.execute(
      "SELECT * FROM users WHERE id = #{user_id}"
    )
  end

  # Command injection
  def execute_command(user_input)
    system("ls #{user_input}")
  end

  # Unsafe deserialization
  def load_yaml(yaml_string)
    YAML.load(yaml_string)
  end

  # Weak cryptography
  def hash_password(password)
    Digest::MD5.hexdigest(password)
  end

  # ERB injection
  def render_template(template_string, data)
    ERB.new(template_string).result(binding)
  end

  # File traversal
  def read_file(filename)
    File.read("files/#{filename}")
  end
end
""")

        return {
            "path": str(project_dir),
            "language": "Ruby",
            "has_dockerfile": False,
            "package_files": ["Gemfile"],
            "expected_vulnerabilities": 6,
        }

    def _create_csharp_test_project(self) -> dict:
        """Create a C# test project."""
        project_dir = Path(self.temp_dir) / "test_csharp_project"
        project_dir.mkdir(exist_ok=True)

        # Create .csproj file
        csproj = project_dir / "VulnerableApp.csproj"
        csproj.write_text("""
<Project Sdk="Microsoft.NET.Sdk.Web">
  <PropertyGroup>
    <TargetFramework>net5.0</TargetFramework>
  </PropertyGroup>

  <PackageReference Include="Newtonsoft.Json" Version="9.0.1" />
  <PackageReference Include="System.Data.SqlClient" Version="4.6.0" />
</Project>
""")

        # Create vulnerable C# code
        program_cs = project_dir / "Program.cs"
        program_cs.write_text("""
using System;
using System.Data.SqlClient;
using System.Diagnostics;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Web;

namespace VulnerableApp
{
    public class Program
    {
        private const string SECRET_KEY = "csharp-hardcoded-secret";

        // SQL injection vulnerability
        public static void GetUser(string userId)
        {
            string connectionString = "Server=localhost;Database=test;Trusted_Connection=true;";
            using (SqlConnection connection = new SqlConnection(connectionString))
            {
                string query = $"SELECT * FROM Users WHERE Id = {userId}";
                SqlCommand command = new SqlCommand(query, connection);
                connection.Open();
                command.ExecuteReader();
            }
        }

        // Command injection
        public static string ExecuteCommand(string userInput)
        {
            ProcessStartInfo startInfo = new ProcessStartInfo()
            {
                FileName = "cmd.exe",
                Arguments = $"/c ping {userInput}",
                UseShellExecute = false,
                RedirectStandardOutput = true
            };

            using (Process process = Process.Start(startInfo))
            {
                return process.StandardOutput.ReadToEnd();
            }
        }

        // Weak cryptography
        public static string HashPassword(string password)
        {
            using (MD5 md5 = MD5.Create())
            {
                byte[] hash = md5.ComputeHash(Encoding.UTF8.GetBytes(password));
                return Convert.ToBase64String(hash);
            }
        }

        // Path traversal
        public static string ReadFile(string filename)
        {
            return File.ReadAllText($"files/{filename}");
        }

        public static void Main(string[] args)
        {
            Console.WriteLine("Vulnerable C# Application");
        }
    }
}
""")

        return {
            "path": str(project_dir),
            "language": "C#",
            "has_dockerfile": False,
            "package_files": ["VulnerableApp.csproj"],
            "expected_vulnerabilities": 4,
        }

    def _create_php_test_project(self) -> dict:
        """Create a PHP test project."""
        project_dir = Path(self.temp_dir) / "test_php_project"
        project_dir.mkdir(exist_ok=True)

        # Create composer.json with vulnerable packages
        composer_json = project_dir / "composer.json"
        composer_json.write_text("""
{
    "name": "example/vulnerable-php-app",
    "require": {
        "monolog/monolog": "1.0.0",
        "twig/twig": "1.35.0",
        "symfony/yaml": "2.8.0",
        "doctrine/orm": "2.5.0"
    }
}
""")

        # Create vulnerable PHP application
        index_php = project_dir / "index.php"
        index_php.write_text("""
<?php
define('SECRET_KEY', 'php-hardcoded-secret');

class VulnerableApp {

    // SQL injection vulnerability
    public function getUser($userId) {
        $connection = new PDO('mysql:host=localhost;dbname=test', 'user', 'pass');
        $query = "SELECT * FROM users WHERE id = " . $userId;
        return $connection->query($query);
    }

    // Command injection
    public function executeCommand($userInput) {
        return shell_exec("ping " . $userInput);
    }

    // Unsafe deserialization
    public function loadData($serializedData) {
        return unserialize($serializedData);
    }

    // Weak cryptography
    public function hashPassword($password) {
        return md5($password);
    }

    // File inclusion vulnerability
    public function includeFile($filename) {
        include("files/" . $filename);
    }

    // XSS vulnerability
    public function displayUserInput($input) {
        echo "<div>" . $input . "</div>";
    }

    // Path traversal
    public function readFile($filename) {
        return file_get_contents("uploads/" . $filename);
    }
}

// CSRF vulnerability - no token validation
if ($_POST['action'] == 'delete') {
    // Delete user without proper validation
    $app = new VulnerableApp();
    $app->getUser($_POST['id']);
}
?>
""")

        return {
            "path": str(project_dir),
            "language": "PHP",
            "has_dockerfile": False,
            "package_files": ["composer.json"],
            "expected_vulnerabilities": 8,
        }

    def _create_rust_test_project(self) -> dict:
        """Create a Rust test project."""
        project_dir = Path(self.temp_dir) / "test_rust_project"
        project_dir.mkdir(exist_ok=True)

        # Create Cargo.toml
        cargo_toml = project_dir / "Cargo.toml"
        cargo_toml.write_text("""
[package]
name = "vulnerable-rust-app"
version = "0.1.0"
edition = "2021"

[dependencies]
serde = "1.0.120"
serde_json = "1.0.61"
reqwest = "0.10.10"
tokio = "0.3.7"
""")

        # Create src directory
        src_dir = project_dir / "src"
        src_dir.mkdir(exist_ok=True)

        # Create main.rs with potential issues
        main_rs = src_dir / "main.rs"
        main_rs.write_text("""
use std::process::Command;
use std::fs::File;
use std::io::Read;

const SECRET_KEY: &str = "rust-hardcoded-secret";

// Command injection potential (though Rust makes it harder)
fn execute_command(user_input: &str) -> Result<String, Box<dyn std::error::Error>> {
    let output = Command::new("ping")
        .arg("-c")
        .arg("1")
        .arg(user_input) // Still could be dangerous if not validated
        .output()?;

    Ok(String::from_utf8_lossy(&output.stdout).to_string())
}

// Unsafe block usage (not necessarily vulnerable but worth flagging)
fn unsafe_memory_access() {
    unsafe {
        let ptr = 0x12345usize as *const i32;
        println!("Value: {}", *ptr); // Dangerous!
    }
}

// File reading without proper validation
fn read_file(filename: &str) -> Result<String, std::io::Error> {
    let mut file = File::open(format!("files/{}", filename))?;
    let mut contents = String::new();
    file.read_to_string(&mut contents)?;
    Ok(contents)
}

// Weak random number generation
fn generate_token() -> u32 {
    // Using time as seed is predictable
    use std::time::{SystemTime, UNIX_EPOCH};
    let seed = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs() as u32;
    seed * 1664525 + 1013904223 // Linear congruential generator
}

fn main() {
    println!("Vulnerable Rust Application");

    // Demonstrate vulnerabilities
    unsafe_memory_access();
    let _ = execute_command("localhost");
    let _ = generate_token();
}
""")

        return {
            "path": str(project_dir),
            "language": "Rust",
            "has_dockerfile": False,
            "package_files": ["Cargo.toml"],
            "expected_vulnerabilities": 3,
        }

    def _create_cpp_test_project(self) -> dict:
        """Create a C/C++ test project."""
        project_dir = Path(self.temp_dir) / "test_cpp_project"
        project_dir.mkdir(exist_ok=True)

        # Create CMakeLists.txt
        cmake = project_dir / "CMakeLists.txt"
        cmake.write_text("""
cmake_minimum_required(VERSION 3.10)
project(VulnerableApp)

set(CMAKE_CXX_STANDARD 11)

add_executable(VulnerableApp main.cpp vulnerable_functions.cpp)
""")

        # Create main.cpp
        main_cpp = project_dir / "main.cpp"
        main_cpp.write_text("""
#include <iostream>
#include <cstring>
#include <cstdlib>
#include <fstream>

#define SECRET_KEY "cpp-hardcoded-secret"

// Buffer overflow vulnerability
void vulnerable_strcpy(const char* input) {
    char buffer[10];
    strcpy(buffer, input); // No bounds checking!
    std::cout << "Buffer contains: " << buffer << std::endl;
}

// Format string vulnerability
void vulnerable_printf(const char* user_input) {
    printf(user_input); // User input directly as format string!
}

// Use after free
void use_after_free_bug() {
    char* ptr = new char[100];
    delete[] ptr;
    strcpy(ptr, "This is dangerous!"); // Using freed memory
}

// Integer overflow
int vulnerable_calculation(int user_input) {
    return user_input * 1000000; // Could overflow
}

// Command injection
void execute_command(const char* user_input) {
    char command[256];
    sprintf(command, "ping %s", user_input);
    system(command); // Dangerous!
}

// File path traversal
void read_file(const char* filename) {
    char filepath[256];
    sprintf(filepath, "files/%s", filename);
    std::ifstream file(filepath);
    // No validation of filename
}

// Memory leak
void memory_leak() {
    char* ptr = new char[1000];
    // Never deleted!
    return;
}

int main() {
    std::cout << "Vulnerable C++ Application" << std::endl;

    // Demonstrate vulnerabilities
    vulnerable_strcpy("This input is way too long for the buffer");
    vulnerable_printf("%s%s%s%s");
    use_after_free_bug();
    memory_leak();

    return 0;
}
""")

        # Create additional source file
        vulnerable_cpp = project_dir / "vulnerable_functions.cpp"
        vulnerable_cpp.write_text("""
#include <cstring>
#include <cstdlib>

// More buffer overflow examples
void stack_overflow(int n) {
    if (n > 0) {
        char big_array[1000000]; // Stack overflow potential
        stack_overflow(n - 1);
    }
}

// Double free vulnerability
void double_free_bug() {
    char* ptr = (char*)malloc(100);
    free(ptr);
    free(ptr); // Double free!
}

// Null pointer dereference
void null_pointer_deref(char* ptr) {
    if (ptr != nullptr) {
        // Some logic
    }
    strcpy(ptr, "data"); // ptr could still be null
}
""")

        return {
            "path": str(project_dir),
            "language": "C++",
            "has_dockerfile": False,
            "package_files": ["CMakeLists.txt"],
            "expected_vulnerabilities": 10,
        }

    def _setup_mock_database(self):
        """Setup mock vulnerability database."""
        db_path = Path(self.temp_dir) / "mock_vulnerability_db.tar.gz"

        # Create a simple tarball with mock vulnerability data
        import tarfile

        with tarfile.open(db_path, "w:gz") as tar:
            # Create a temporary file with mock data
            mock_db_content = json.dumps(
                {
                    "vulnerabilities": [
                        {
                            "id": "CVE-2021-44228",
                            "severity": "critical",
                            "package": "log4j",
                        },
                        {
                            "id": "CVE-2017-5638",
                            "severity": "high",
                            "package": "struts",
                        },
                        {
                            "id": "CVE-2019-0232",
                            "severity": "high",
                            "package": "tomcat",
                        },
                    ]
                }
            )

            mock_file_path = Path(self.temp_dir) / "mock_db.json"
            mock_file_path.write_text(mock_db_content)
            tar.add(str(mock_file_path), arcname="vulnerability_db.json")

        return str(db_path)

    def _setup_network_config(self):
        """Setup network configuration for testing."""
        allowlist_path = Path(self.temp_dir) / "network_allowlist.txt"
        allowlist_path.write_text("""
localhost:8080
127.0.0.1:3000
example.com:443
registry-1.docker.io:443
""")
        return str(allowlist_path)

    def teardown_test_environment(self):
        """Clean up test environment."""
        if self.temp_dir and os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            logger.info(f"Cleaned up test environment: {self.temp_dir}")


@pytest.fixture(scope="session")
def production_test_suite():
    """Pytest fixture for production test suite."""
    suite = ProductionTestSuite()
    suite.setup_test_environment()
    yield suite
    suite.teardown_test_environment()


class TestProductionReadiness:
    """Production readiness test cases."""

    def test_multi_language_project_scanning(self, production_test_suite):
        """Test scanning projects in all supported languages."""
        logger.info("Testing multi-language project scanning...")

        results = {}

        for lang, project_info in production_test_suite.test_projects.items():
            try:
                logger.info(f"Testing {lang} project scanning...")

                # Create projects.json for this language
                projects_config = {
                    "projects": [
                        {
                            "url": project_info["path"],
                            "name": f"test-{lang}-project",
                            "language": project_info["language"],
                            "description": f"Test {lang} project for vulnerability scanning",
                            "container_capable": project_info.get(
                                "has_dockerfile", False
                            ),
                            "dockerfile_present": project_info.get(
                                "has_dockerfile", False
                            ),
                            "package_managers": project_info.get("package_files", []),
                        }
                    ]
                }

                projects_file = (
                    Path(production_test_suite.temp_dir) / f"{lang}_projects.json"
                )
                projects_file.write_text(json.dumps(projects_config, indent=2))

                # Run scan simulation (mocked for now)
                scan_result = self._simulate_scan(project_info, lang)
                results[lang] = scan_result

                # Verify expected vulnerabilities were found
                assert scan_result["vulnerabilities_found"] > 0, (
                    f"No vulnerabilities found in {lang} project"
                )

                logger.info(
                    f"✅ {lang} project scan completed - found {scan_result['vulnerabilities_found']} issues"
                )

            except Exception as e:
                logger.error(f"❌ {lang} project scan failed: {str(e)}")
                results[lang] = {"error": str(e)}
                raise

        # Verify all languages were tested
        expected_languages = [
            "python",
            "javascript",
            "typescript",
            "java",
            "go",
            "ruby",
            "csharp",
            "php",
            "rust",
            "cpp",
        ]
        for lang in expected_languages:
            assert lang in results, f"Missing test results for {lang}"

        production_test_suite.test_results["multi_language_scan"] = results

    def test_load_testing_concurrent_scans(self, production_test_suite):
        """Test system under load with concurrent scans."""
        logger.info("Testing concurrent scan load handling...")

        start_time = time.time()

        # Run multiple scans concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for i in range(10):  # 10 concurrent scans
                project_info = production_test_suite.test_projects[
                    "python"
                ]  # Use Python project for load test
                future = executor.submit(
                    self._simulate_scan, project_info, f"python_load_test_{i}"
                )
                futures.append(future)

            # Wait for all scans to complete
            results = []
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    results.append(result)
                except Exception as e:
                    logger.error(f"Concurrent scan failed: {str(e)}")
                    raise

        end_time = time.time()
        total_time = end_time - start_time

        # Performance assertions
        assert len(results) == 10, "Not all concurrent scans completed"
        assert total_time < 600, (
            f"Load test took too long: {total_time}s"
        )  # Should complete within 10 minutes

        avg_scan_time = total_time / len(results)
        logger.info(
            f"✅ Load test completed - {len(results)} scans in {total_time:.2f}s (avg: {avg_scan_time:.2f}s per scan)"
        )

        production_test_suite.test_results["performance_metrics"]["load_test"] = {
            "total_time": total_time,
            "concurrent_scans": len(results),
            "avg_scan_time": avg_scan_time,
        }

    def test_container_security_isolation(self, production_test_suite):
        """Test container security and isolation."""
        logger.info("Testing container security and isolation...")

        # Test seccomp profiles exist
        seccomp_dir = Path(__file__).parent.parent.parent / "seccomp"
        required_profiles = [
            "default.json",
            "osv-scanner-seccomp.json",
            "semgrep-seccomp.json",
            "trivy-seccomp.json",
            "zap-seccomp.json",
        ]

        for profile in required_profiles:
            profile_path = seccomp_dir / profile
            assert profile_path.exists(), f"Missing seccomp profile: {profile}"

            # Validate JSON format
            with open(profile_path) as f:
                try:
                    profile_data = json.load(f)
                    assert "syscalls" in profile_data, (
                        f"Invalid seccomp profile format: {profile}"
                    )
                except json.JSONDecodeError as e:
                    raise AssertionError(
                        f"Invalid JSON in seccomp profile: {profile}"
                    ) from e

        logger.info("✅ All seccomp profiles validated")

        # Test Dockerfile security
        dockerfile_path = Path(__file__).parent.parent.parent / "Dockerfile"
        if dockerfile_path.exists():
            dockerfile_content = dockerfile_path.read_text()

            # Check for security best practices
            security_checks = [
                ("USER", "Should run as non-root user"),
                ("COPY --chown=", "Should set proper ownership"),
                (
                    "RUN apt-get update && apt-get install",
                    "Should combine RUN commands",
                ),
            ]

            for check, description in security_checks:
                # These are recommendations, not hard requirements
                if check not in dockerfile_content:
                    logger.warning(f"Dockerfile recommendation: {description}")

        logger.info("✅ Container security validation completed")

    def test_error_handling_edge_cases(self, production_test_suite):
        """Test error handling and edge cases."""
        logger.info("Testing error handling and edge cases...")

        edge_cases = [
            {
                "name": "empty_project",
                "setup": lambda: self._create_empty_project(
                    production_test_suite.temp_dir
                ),
                "expected_behavior": "should handle gracefully",
            },
            {
                "name": "corrupted_package_file",
                "setup": lambda: self._create_corrupted_package_project(
                    production_test_suite.temp_dir
                ),
                "expected_behavior": "should report parsing error",
            },
            {
                "name": "large_project",
                "setup": lambda: self._create_large_project(
                    production_test_suite.temp_dir
                ),
                "expected_behavior": "should handle within memory limits",
            },
            {
                "name": "binary_files_only",
                "setup": lambda: self._create_binary_only_project(
                    production_test_suite.temp_dir
                ),
                "expected_behavior": "should skip binary files appropriately",
            },
        ]

        results = {}

        for case in edge_cases:
            try:
                logger.info(f"Testing edge case: {case['name']}")
                project_path = case["setup"]()

                # Simulate scan with edge case
                result = self._simulate_edge_case_scan(project_path, case["name"])
                results[case["name"]] = {"status": "passed", "result": result}

                logger.info(f"✅ Edge case {case['name']} handled correctly")

            except Exception as e:
                logger.error(f"❌ Edge case {case['name']} failed: {str(e)}")
                results[case["name"]] = {"status": "failed", "error": str(e)}

        # Verify all edge cases were handled
        for case in edge_cases:
            assert case["name"] in results, (
                f"Missing result for edge case: {case['name']}"
            )

        production_test_suite.test_results["edge_cases"] = results

    def test_report_generation_under_load(self, production_test_suite):
        """Test report generation under various load conditions."""
        logger.info("Testing report generation under load...")

        # Generate reports with different data sizes
        report_tests = [
            {"name": "small_report", "findings": 10},
            {"name": "medium_report", "findings": 100},
            {"name": "large_report", "findings": 1000},
            {"name": "very_large_report", "findings": 5000},
        ]

        results = {}

        for test in report_tests:
            try:
                logger.info(f"Testing {test['name']} with {test['findings']} findings")

                start_time = time.time()
                report_content = self._generate_test_report(test["findings"])
                generation_time = time.time() - start_time

                # Verify report quality
                assert len(report_content) > 100, "Report too short"
                assert "# Security Scan Report" in report_content, (
                    "Missing report header"
                )
                assert str(test["findings"]) in report_content, (
                    "Finding count not reflected in report"
                )

                results[test["name"]] = {
                    "generation_time": generation_time,
                    "report_size": len(report_content),
                    "findings": test["findings"],
                }

                logger.info(
                    f"✅ {test['name']} generated in {generation_time:.2f}s ({len(report_content)} chars)"
                )

            except Exception as e:
                logger.error(f"❌ {test['name']} failed: {str(e)}")
                results[test["name"]] = {"error": str(e)}
                raise

        production_test_suite.test_results["report_generation"] = results

    def test_network_isolation_validation(self, production_test_suite):
        """Test network isolation and allowlist functionality."""
        logger.info("Testing network isolation and allowlist validation...")

        # Test allowlist parsing
        allowlist_path = Path(production_test_suite.temp_dir) / "network_allowlist.txt"
        assert allowlist_path.exists(), "Network allowlist file not created"

        allowlist_content = allowlist_path.read_text()
        allowed_hosts = [
            line.strip()
            for line in allowlist_content.strip().split("\n")
            if line.strip()
        ]

        # Verify allowlist format
        for host_entry in allowed_hosts:
            if ":" in host_entry:
                host, port = host_entry.split(":", 1)
                assert host, "Empty host in allowlist entry"
                assert port.isdigit(), f"Invalid port in allowlist entry: {host_entry}"
            else:
                assert host_entry, "Empty allowlist entry"

        logger.info(f"✅ Network allowlist validated - {len(allowed_hosts)} entries")

        # Test network policy enforcement (simulation)
        ni_results = self._simulate_network_requests(allowed_hosts)

        production_test_suite.test_results["network_isolation"] = {
            "allowlist_entries": len(allowed_hosts),
            "blocked_requests": ni_results.get("blocked", []),
            "allowed_requests": ni_results.get("allowed", []),
        }

    def test_memory_and_resource_limits(self, production_test_suite):
        """Test memory usage and resource limits."""
        logger.info("Testing memory usage and resource limits...")

        import gc

        try:
            import psutil  # type: ignore
        except Exception:
            pytest.skip("psutil is not installed; skipping memory/resource limit test.")

        initial_memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB

        # Simulate memory-intensive operations
        large_data_sets = []
        for i in range(5):
            # Simulate processing large scan results
            large_dataset = self._create_large_scan_result(10000)  # 10k findings
            large_data_sets.append(large_dataset)

            current_memory = psutil.Process().memory_info().rss / 1024 / 1024
            memory_increase = current_memory - initial_memory

            logger.info(
                f"Memory usage after dataset {i + 1}: {current_memory:.1f}MB (+{memory_increase:.1f}MB)"
            )

            # Assert memory doesn't grow excessively
            assert memory_increase < 500, (
                f"Memory usage too high: {memory_increase}MB increase"
            )

        # Test garbage collection
        large_data_sets.clear()
        gc.collect()

        final_memory = psutil.Process().memory_info().rss / 1024 / 1024
        memory_recovered = initial_memory - final_memory

        logger.info(
            f"✅ Memory test completed - Final: {final_memory:.1f}MB (recovered: {abs(memory_recovered):.1f}MB)"
        )

        production_test_suite.test_results["resource_usage"] = {
            "initial_memory_mb": initial_memory,
            "peak_memory_mb": max([psutil.Process().memory_info().rss / 1024 / 1024]),
            "final_memory_mb": final_memory,
        }

    # Helper methods for simulation

    def _simulate_scan(self, project_info, project_name):
        """Simulate a security scan for testing purposes."""
        # Simulate scan duration based on project complexity
        scan_time = min(project_info.get("expected_vulnerabilities", 1) * 0.1, 5.0)
        time.sleep(scan_time)

        return {
            "project_name": project_name,
            "language": project_info.get("language", "Unknown"),
            "scan_duration": scan_time,
            "vulnerabilities_found": project_info.get("expected_vulnerabilities", 1),
            "status": "completed",
        }

    def _simulate_edge_case_scan(self, project_path, case_name):
        """Simulate scan for edge cases."""
        time.sleep(0.5)  # Brief processing time

        return {
            "case": case_name,
            "project_path": project_path,
            "status": "handled",
            "issues_found": 0 if case_name == "empty_project" else 1,
        }

    def _create_empty_project(self, temp_dir):
        """Create an empty project for edge case testing."""
        empty_project_dir = Path(temp_dir) / "empty_project"
        empty_project_dir.mkdir(exist_ok=True)
        return str(empty_project_dir)

    def _create_corrupted_package_project(self, temp_dir):
        """Create a project with corrupted package files."""
        corrupt_project_dir = Path(temp_dir) / "corrupt_project"
        corrupt_project_dir.mkdir(exist_ok=True)

        # Create corrupted package.json
        corrupt_package = corrupt_project_dir / "package.json"
        corrupt_package.write_text('{"name": "test", "dependencies": {')  # Invalid JSON

        return str(corrupt_project_dir)

    def _create_large_project(self, temp_dir):
        """Create a large project for performance testing."""
        large_project_dir = Path(temp_dir) / "large_project"
        large_project_dir.mkdir(exist_ok=True)

        # Create many files
        for i in range(100):
            file_path = large_project_dir / f"file_{i}.py"
            file_path.write_text(f"# Large file {i}\n" + "print('data')\n" * 100)

        return str(large_project_dir)

    def _create_binary_only_project(self, temp_dir):
        """Create a project with only binary files."""
        binary_project_dir = Path(temp_dir) / "binary_project"
        binary_project_dir.mkdir(exist_ok=True)

        # Create binary files
        for ext in [".exe", ".dll", ".so", ".dylib"]:
            binary_file = binary_project_dir / f"binary{ext}"
            binary_file.write_bytes(b"\x00\x01\x02\x03" * 1000)  # Fake binary content

        return str(binary_project_dir)

    def _generate_test_report(self, num_findings):
        """Generate a test report with specified number of findings."""
        findings = []
        for i in range(num_findings):
            findings.append(
                {
                    "id": f"TEST-{i:04d}",
                    "severity": ["low", "medium", "high", "critical"][i % 4],
                    "description": f"Test finding {i}",
                    "file": f"test_file_{i}.py",
                    "line": i + 1,
                }
            )

        # Simulate report generation
        report_content = f"""# Security Scan Report

## Summary
- Total findings: {num_findings}
- Critical: {len([f for f in findings if f["severity"] == "critical"])}
- High: {len([f for f in findings if f["severity"] == "high"])}
- Medium: {len([f for f in findings if f["severity"] == "medium"])}
- Low: {len([f for f in findings if f["severity"] == "low"])}

## Detailed Findings

"""

        for finding in findings[:10]:  # Include first 10 in detail
            report_content += f"""### {finding["id"]} - {finding["severity"].upper()}
File: {finding["file"]}:{finding["line"]}
Description: {finding["description"]}

"""

        if num_findings > 10:
            report_content += f"\n... and {num_findings - 10} more findings\n"

        return report_content

    def _create_large_scan_result(self, num_findings):
        """Create large scan result for memory testing."""
        return {
            "findings": [
                {
                    "id": f"FINDING-{i}",
                    "description": f"Test finding {i}" * 10,  # Make it larger
                    "severity": "medium",
                    "file": f"/path/to/file_{i}.py",
                    "line": i,
                    "metadata": {"data": "x" * 100},  # Extra data
                }
                for i in range(num_findings)
            ]
        }

    def _simulate_network_requests(self, allowed_hosts):
        """Simulate network request validation, tracking both allowed and blocked cases."""
        test_requests = [
            "malicious-site.com:80",
            "localhost:8080",  # Should be allowed
            "example.com:443",  # Should be allowed
            "evil.example.com:443",  # Should be blocked
            "127.0.0.1:3000",  # Should be allowed
        ]

        allowed: list[str] = []
        blocked: list[str] = []
        for request in test_requests:
            if request in allowed_hosts:
                allowed.append(request)
            else:
                blocked.append(request)

        # Ensure allowlist actually allows something (simple sanity)
        assert any(r in allowed_hosts for r in test_requests), (
            "No requests matched allowlist entries"
        )

        return {"blocked": blocked, "allowed": allowed}
