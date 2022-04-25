//
// Created by panyansong on 2021/11/3.
//
#define BOOST_BIND_GLOBAL_PLACEHOLDERS
#include <boost/python.hpp>
#include <boost/python/suite/indexing/vector_indexing_suite.hpp>
#include <vector>
#include "game/Game.h"
#include <iostream>
#include <string>

using namespace std;

template <class T>
vector<T> py_to_vector(boost::python::list pyiter) {
    vector<T> vec;
    for (int i = 0; i < len(pyiter); ++i) {
        vec.push_back(boost::python::extract<T>(pyiter[i]));
    }
    return vec;
}

template <class T>
vector<vector<T>> py_to_vector_2d(boost::python::list pylist) {
    vector<vector<T>> vec;
    for (int i = 0; i < len(pylist); ++i) {
        boost::python::list l1 = boost::python::extract<boost::python::list>(pylist[i]);
        vector<T> vec1;
        for (int j = 0; j < len(l1); ++j) {
            vec1.push_back(boost::python::extract<T>(l1[j]));
        }
        vec.push_back(vec1);
    }
    return vec;
}

template <class T>
vector<vector<vector<T>>> py_to_vector_3d(boost::python::list pylist) {
    vector<vector<vector<T>>> vec;
    for (int i = 0; i < len(pylist); ++i) {
        boost::python::list l1 = boost::python::extract<boost::python::list>(pylist[i]);
        vector<vector<T>> vec1;
        for (int j = 0; j < len(l1); ++j) {
            boost::python::list l2 = boost::python::extract<boost::python::list>(pylist[i][j]);
            vector<T> vec2;
            for(int k = 0; k < len(l2); ++k) {
                vec2.push_back(boost::python::extract<T>(l2[k]));
            }
            vec1.push_back(vec2);
        }
        vec.push_back(vec1);
    }
    return vec;
}

template <class T>
boost::python::list vector_to_pylist(vector<T> vec) {
    boost::python::list ob;
    for (size_t i = 0; i < vec.size(); ++i) {
        ob.attr("append")(vec[i]);
    }
    return ob;
}

template <class T>
boost::python::list vector_to_pylist_2d(vector<vector<T> > vec) {
    boost::python::list l1;
    for (size_t i = 0; i < vec.size(); ++i) {
        boost::python::list l2;
        for (size_t j = 0; j < vec[i].size(); ++j) {
            l2.attr("append")(vec[i][j]);
        }
        l1.attr("append")(l2);
    }
    return l1;
}

template <class T>
boost::python::list vector_to_pylist_3d(vector<vector<vector<T>>> vec) {
    boost::python::list l1;
    for (size_t i = 0; i < vec.size(); ++i) {
        boost::python::list l2;
        for (size_t j = 0; j < vec[i].size(); ++j) {
            boost::python::list l3;
            for(size_t k = 0; k < vec[i][j].size(); ++k)
            {
                l3.attr("append")(vec[i][j][k]);
            }
            l2.attr("append")(l3);
        }
        l1.attr("append")(l2);
    }
    return l1;
}

void EnvUpdate(Game* game_ptr, boost::python::list py_ob) {
    vector<vector<float>> action = py_to_vector_2d<float>(py_ob);
    game_ptr->update(action);
}

void EnvReset(Game* game_ptr, int seed) {
    game_ptr->reset(seed);
}

// void EnvCreate(Game* game_ptr, const string& configDir) {
//     game_ptr->CreateArea(configDir);
// }

boost::python::str EnvRunScript(Game* game_ptr, const string& script)
{
    return game_ptr->runScript(script).c_str();
}

boost::python::object EnvAgentObserve(Game* game_ptr)
{
    return vector_to_pylist_2d<float>(game_ptr->agentObserve());
}

boost::python::object EnvAgentResult(Game* game_ptr)
{
    return vector_to_pylist_2d<float>(game_ptr->agentResult());
}

boost::python::object EnvAgentCount(Game* game_ptr)
{
    return vector_to_pylist(vector<int>{game_ptr->agentCount()});
}

boost::python::object EnvGetUI(Game* game_ptr, int agent_id)
{
    return vector_to_pylist(game_ptr->getUI(agent_id));
}

BOOST_PYTHON_MODULE(eden_py) {
    boost::python::class_<Game>("Env", boost::python::init<string>())
        .def("reset",       &EnvReset)
        .def("update",      &EnvUpdate)
        .def("result",      &EnvAgentResult)
        .def("observe",     &EnvAgentObserve)
        .def("agent_count", &EnvAgentCount)

        .def("get_ui",      &EnvGetUI)
        .def("run_script",  &EnvRunScript);
}