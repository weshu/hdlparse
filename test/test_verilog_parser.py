import unittest
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hdlparse.verilog_parser import (
    parse_verilog,
    VerilogModule,
    VerilogParameter,
    VerilogSubModule
)

class TestVerilogParser(unittest.TestCase):
    def test_basic_module(self):
        """Test parsing a basic module without ports"""
        verilog = """
        module basic_module();
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        self.assertEqual(modules[0].name, "basic_module")
        self.assertEqual(len(modules[0].ports), 0)

    def test_module_with_ports(self):
        """Test parsing a module with input and output ports"""
        verilog = """
        module port_module(
            input clk,
            output reg [7:0] data
        );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(module.name, "port_module")
        self.assertEqual(len(module.ports), 2)
        
        # Check input port
        clk_port = next(p for p in module.ports if p.name == "clk")
        self.assertEqual(clk_port.mode, "input")
        self.assertEqual(clk_port.data_type, "wire")
        
        # Check output port
        data_port = next(p for p in module.ports if p.name == "data")
        self.assertEqual(data_port.mode, "output")
        self.assertEqual(data_port.data_type, "reg [7:0]")

    def test_module_with_parameters(self):
        """Test parsing a module with parameters"""
        verilog = """
        module param_module #(
            parameter WIDTH = 8,
            parameter [7:0] ADDR = 8'hFF
        )(
            input clk
        );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        
        # Check parameters
        width_param = next(p for p in module.generics if p.name == "WIDTH")
        self.assertEqual(width_param.data_type, "wire")
        self.assertEqual(width_param.default_value, "8")
        
        addr_param = next(p for p in module.generics if p.name == "ADDR")
        self.assertEqual(addr_param.data_type, "wire [7:0]")
        self.assertEqual(addr_param.default_value, "8'hFF")

    def test_module_with_submodules(self):
        """Test parsing a module with submodule instances"""
        verilog = """
        module top_module(
            input clk,
            input rst
        );
            sub_module instance1 (
                .clk(clk),
                .rst(rst)
            );
            
            sub_module instance2 (
                .clk(clk),
                .rst(rst)
            );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(len(module.submodules), 2)
        
        # Check first submodule
        sub1 = module.submodules[0]
        self.assertEqual(sub1.module_type, "sub_module")
        self.assertEqual(sub1.instance_name, "instance1")
        self.assertEqual(sub1.port_connections["clk"], "clk")
        self.assertEqual(sub1.port_connections["rst"], "rst")
        
        # Check second submodule
        sub2 = module.submodules[1]
        self.assertEqual(sub2.module_type, "sub_module")
        self.assertEqual(sub2.instance_name, "instance2")
        self.assertEqual(sub2.port_connections["clk"], "clk")
        self.assertEqual(sub2.port_connections["rst"], "rst")

    def test_module_with_comments(self):
        """Test parsing a module with comments and metacomments"""
        verilog = """
        // This is a test module
        module comment_module(
            input clk,  // Clock input
            output reg data  // Data output
        );
            // Internal comment
            /* Block comment
               spanning multiple lines */
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        self.assertEqual(module.name, "comment_module")
        self.assertEqual(len(module.ports), 2)

    def test_multiple_modules(self):
        """Test parsing multiple modules in the same file"""
        verilog = """
        module module1(
            input clk
        );
        endmodule

        module module2(
            input rst
        );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 2)
        self.assertEqual(modules[0].name, "module1")
        self.assertEqual(modules[1].name, "module2")

    def test_complex_module(self):
        """Test parsing a complex module with all features"""
        verilog = """
        // Complex module test
        module complex_module #(
            parameter WIDTH = 8,
            parameter [7:0] ADDR = 8'hFF
        )(
            input clk,
            input rst_n,
            output reg [WIDTH-1:0] data,
            inout wire sda
        );
            // Submodule instances
            sub_module sub1 (
                .clk(clk),
                .rst(rst_n),
                .data(data)
            );
            
            sub_module sub2 (
                .clk(clk),
                .rst(rst_n),
                .data(data[7:0])
            );
        endmodule
        """
        modules = parse_verilog(verilog)
        self.assertEqual(len(modules), 1)
        module = modules[0]
        
        # Check parameters
        width_param = next(p for p in module.generics if p.name == "WIDTH")
        self.assertEqual(width_param.data_type, "wire")
        self.assertEqual(width_param.default_value, "8")
        
        addr_param = next(p for p in module.generics if p.name == "ADDR")
        self.assertEqual(addr_param.data_type, "wire [7:0]")
        self.assertEqual(addr_param.default_value, "8'hFF")
        
        # Check ports
        self.assertEqual(len(module.ports), 4)
        clk_port = next(p for p in module.ports if p.name == "clk")
        self.assertEqual(clk_port.mode, "input")
        
        data_port = next(p for p in module.ports if p.name == "data")
        self.assertEqual(data_port.mode, "output")
        self.assertEqual(data_port.data_type, "reg [WIDTH-1:0]")
        
        # Check submodules
        self.assertEqual(len(module.submodules), 2)
        sub1 = module.submodules[0]
        self.assertEqual(sub1.module_type, "sub_module")
        self.assertEqual(sub1.instance_name, "sub1")
        self.assertEqual(sub1.port_connections["clk"], "clk")

if __name__ == '__main__':
    unittest.main() 